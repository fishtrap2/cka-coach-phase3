import os
from openai import OpenAI
# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
You are a Certified Kubernetes Administrator training coach.

Use the ELS (Everything Lives Somewhere) 9-layer architecture model.

When answering questions:

1. Identify which ELS layer the component belongs to
2. Explain where the component runs in the Kubernetes stack
3. Suggest debugging commands a student could run
4. Prefer commands that work in a typical cloud lab environment

Be concise and educational.
"""

def ask_llm(question: str, context: str = "") -> str:
    """
    Sends a question to the LLM along with optional cluster context.
    """

    try:

        prompt = question

        if context:
            prompt += f"\n\nCluster Context:\n{context}"

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"LLM error: {str(e)}"


