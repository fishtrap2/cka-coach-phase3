# 🧠 cka-coach Learning Path

cka-coach is designed to teach Kubernetes and modern AI system fundamentals by letting students move the same application through four increasingly realistic layers of execution:

1. **Run from Source**
2. **Run as a Container**
3. **Run as a Pod**
4. **Run as a Service inside the LFS258 cluster**

This is intentional. Students do not just use cka-coach — they also learn how software moves from source code to a running system inside Kubernetes.

---

## Why this learning path exists

A core idea behind cka-coach is that **everything lives somewhere**.

Students often learn Kubernetes as disconnected facts:
- source code in one place  
- containers in another  
- Pods and Services somewhere else  
- AI as a black box on top  

cka-coach uses the same application to walk through these layers in sequence so the student can build a more concrete mental model:

> **Code → Container → Pod → Service**

This makes the platform itself part of the lesson.

---

# Level 1 — Run from Source (Git + Python)

## What the student learns

- cloning a repository  
- checking out a versioned release  
- creating and activating a Python virtual environment  
- installing dependencies from `requirements.txt`  
- running an application directly from source code  

## What the student does


```console
git clone <repo-url>
cd cka-coach
git checkout v0.4.1

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=your_key_here

streamlit run ui/dashboard.py
```


## mental model
> “I prepare my machine to run the app.”

## Why this matters

At this level, the student sees the application in its most direct form:

- source code on disk
- dependencies installed into a local environment
- the app launched manually

This is the best level for understanding how the codebase is organized and for making changes during development.

# Level 2 — Run as a Container (Docker)

## What the student learns
- what a container image is
- the difference between build and run
- the difference between an image and a container
- how environment variables are passed at runtime
- how port mapping works

## What the student does
> docker build -t cka-coach:v0.4.1 .
> docker run -p 8501:8501 \
>   -e OPENAI_API_KEY=your_key_here \
>   cka-coach:v0.4.1

## Mental Model
> “The app is already packaged — I just run it.”

## Key teaching moment
Students should understand the difference between:
- Image → the packaged artifact
- Container → the running process created from that artifact
## Why this matters

At this level, students learn that the application no longer depends on manually recreating the Python environment on the host.

The code, runtime, and dependencies are packaged into a reusable artifact.

This is the transition from:

> “prepare the machine”

to

> “run the package”

# Level 3 — Run as a Pod (Kubernetes primitive)
## What the student learns
- A Pod as Kubernetes’ basic workload unit
- how Kubernetes runs containers on a node
- the role of kubelet and the container runtime
- how environment variables are defined in Kubernetes
- how local images can be used in a learning environment
## Example Pod
```console
apiVersion: v1
kind: Pod
metadata:
  name: cka-coach
  namespace: test
spec:
  containers:
    - name: cka-coach
      image: cka-coach:v0.4.1
      imagePullPolicy: Never
      ports:
        - containerPort: 8501
      env:
        - name: OPENAI_API_KEY
          value: "your-key-here"
```
## Apply it
>kubectl apply -f pod.yaml
>kubectl get pods -n test

## Mental model

>“Kubernetes runs my container for me.”

## Why this matters

This is where students begin to see the relationship between:

- the container image they built earlier
_ the Pod abstraction
- the node-level runtime that actually launches the container

It is also the first time cka-coach itself becomes a Kubernetes workload.

# Level 4 — Run as a Service (in-cluster system)
## What the student learns
- the difference between a Pod and a Deployment
- why Services exist
- how a workload is exposed on the network
- basic NodePort access in a lab environment
- how a packaged application becomes a cluster-native system
## Example Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cka-coach
  namespace: test
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cka-coach
  template:
    metadata:
      labels:
        app: cka-coach
    spec:
      containers:
        - name: cka-coach
          image: cka-coach:v0.4.1
          imagePullPolicy: Never
          ports:
            - containerPort: 8501
          env:
            - name: OPENAI_API_KEY
              value: "your-key-here"
## Example Service (NodePort)
>apiVersion: v1
>kind: Service
>metadata:
>  name: cka-coach
>  namespace: test
>spec:
>  type: NodePort
>  selector:
>    app: cka-coach
>  ports:
>    - port: 8501
>      targetPort: 8501
>      nodePort: 30001
## Access it
>http://<node-ip>:30001

## Mental model

>“My app is now a real service inside the cluster.”

## Why this matters

At this level, students move from running a single workload to exposing a usable in-cluster application.

This is the point where cka-coach is no longer just:

- a repo
- or a local container

It becomes a service living inside the Kubernetes system it helps explain.

# Why this 4-level structure matters

cka-coach teaches the same application across four layers:

Level	Concept
1	Code execution
2	Packaging and runtime isolation
3	Orchestration primitive (Pod)
4	Cluster service abstraction

The key idea is simple:

>The same application moves through all layers.

That continuity helps students understand how software actually moves from source code to a running platform workload.
