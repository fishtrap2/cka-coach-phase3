# Secrets and Credentials Rules

cka-coach handles two categories of secrets:
- LLM API keys (OpenAI and future providers)
- Cloud credentials (AWS and future providers)

These rules apply to all code, configuration, documentation, and scripts in this repo.

---

## Absolute rules — never break these

- Never commit secrets, API keys, credentials, or tokens to the repo
- Never log secrets to stdout, stderr, or the Streamlit UI
- Never pass secrets as command-line arguments (visible in `ps aux`)
- Never embed secrets in Docker images or container build artifacts
- Never write secrets to files outside of designated secret paths
- Never include real secrets in documentation, learning moments, or chat logs

---

## LLM API key rules

### Local development (Mac)
- Store in `.env` file at repo root
- `.env` is in `.gitignore` — never remove this entry
- `.env.example` shows the required keys with placeholder values only
- Load via `python-dotenv` — already implemented in `agent.py`

### On a VM / cluster node
- Set as an environment variable in the SSH session before running cka-coach:
  ```bash
  export OPENAI_API_KEY=<your-key>
  streamlit run ui/dashboard.py --allow-host-evidence
  ```
- Do not write the key to any file on the VM
- Do not add it to `.bashrc` or `.profile` on a shared or lab VM

### Future providers
- cka-coach should support multiple LLM providers via a config file
- The config file names the provider and the env var to read the key from
- The config file never holds the key itself
- Example: `LLM_PROVIDER=openai`, `LLM_API_KEY_ENV=OPENAI_API_KEY`

---

## Cloud credential rules

### Local development (Mac)
- Use `~/.aws/credentials` configured via `aws configure`
- Use a dedicated IAM user (`cka-coach-admin`) with least-privilege permissions
- Never use root credentials for day-to-day work
- Rotate keys if they are ever exposed in a chat, log, or screen share

### On a VM / cluster node (preferred approach)
- Attach an IAM role to the EC2 instance
- The AWS SDK picks up the role automatically via the instance metadata service
- No credentials file needed on the VM — nothing to leak
- This is the correct AWS answer for any workload running on EC2

### IAM role minimum permissions for cka-coach on EC2
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Repo safety guarantees

cka-coach itself will not cause a student to leak secrets if they:
- Clone the repo
- Follow the setup instructions
- Use `.env` for local keys

The repo guarantees:
- `.env` and `.env.*` are in `.gitignore`
- `~/.aws/credentials` is never read or copied by any cka-coach script
- No secret scanning bypass comments are permitted in code
- `.env.example` contains only placeholder values

---

## What cka-coach cannot guarantee

- A student who manually adds secrets to tracked files and commits them
- A student who forks the repo and adds secrets to their fork
- Secrets set as environment variables being visible to other processes on the same VM

These are outside cka-coach's control. The secrets management lesson should
teach students how to avoid these risks.

---

## Future secrets management lesson

A dedicated lesson should cover:
- Why secrets management matters (real cost of a leaked key)
- AWS IAM roles vs access keys — when to use each
- Environment variables vs secret managers (AWS Secrets Manager, HashiCorp Vault)
- How to rotate a leaked key
- How to audit what has access to your secrets
- GitHub secret scanning and how to enable it on a fork

This lesson maps to ELS L0 (cloud credentials) and L7 (Kubernetes Secrets objects).

---

## ELS mapping

| Secret type | ELS layer | Notes |
|---|---|---|
| AWS credentials | L0 | Infrastructure access |
| LLM API key | L9 / external | Application-level external dependency |
| Kubernetes Secrets | L7 | Desired-state objects in the API |
| Pod environment variables | L8 | Runtime secret injection into pods |
