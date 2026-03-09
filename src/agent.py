from openai import OpenAI
client = OpenAI()
SYSTEM_PROMPT = """
You are a Certified Kubernetes Administrator training coach.
Use the ELS 9-layer architecture model.
When answering questions:
1. Identify the ELS layer
2. Explain where the component runs
3. Suggest debugging commands
"""
def ask_llm(question, context=""):
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question + "\n\n" + context},
        ],
    )
    return response.choices[0].message.content

