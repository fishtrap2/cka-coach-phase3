# cka-coach (MVP)
AI-powered Kubernetes architecture coach using the ELS model
Everything Lives Somewhere (ELS) architecture model.
## Features
- Shows Kubernetes architecture layers
- Queries a real cluster
- AI explains cluster components
## Commands
Show architecture layers:
python src/main.py layers
Scan cluster:
python src/main.py scan
Ask the AI coach:
python src/main.py ask "where does kubelet run?"
## Requirements
- kubectl
- crictl
- Python 3.10+
## Vision
CKA Coach will evolve into:
- a Kubernetes architecture debugger
- a training assistant for CKA / CKAD
- a visual cluster map

