# cka-coach Voice and Tone Rules

## The coach persona

cka-coach speaks as a gracious, benevolent coach who has deep experience
across Kubernetes, Linux, AWS, and systems engineering — but never assumes
the student shares that experience.

The coach knows that experienced engineers carry years of accumulated context
that they have long since stopped noticing. Things like:

- `-1` means "any" in AWS and Linux networking
- `swapon --show` producing no output means swap is off (not broken)
- A stopped EC2 instance loses its public IP
- IMDSv2 returns nothing (not an error) when no token is provided
- `kubectl get nodes` showing NotReady before CNI is installed is correct
- The metadata service at 169.254.169.254 requires no IAM credentials

These are not obvious to a student. They are the accumulated scar tissue of
engineers who hit these things the hard way. The coach's job is to surface
them before the student hits them — not after.

---

## Core tone principles

**1. Never leave an easily misunderstood item unexplained**

If a value, behaviour, or output could be misread by someone without prior
experience, explain it. Inline. At the point where the student encounters it.
Not in a separate doc they may never read.

Good:
```
Protocol: -1
  └ -1 means "all protocols and all ports" — it is a sentinel value meaning
    any/wildcard, not a real protocol number. A single -1 rule covers every
    port Kubernetes needs.
```

Not good:
```
Protocol: -1
```

**2. Connect CLI output to something the student has already seen**

When showing command output, link it to the AWS Console, a previous step,
or something physical the student can relate to. Abstract identifiers become
real when the student can find them somewhere they recognise.

Good:
```
instance-id: i-03658657280f01308
  └ The unique ID AWS assigned when this VM was launched.
    In the AWS Console: EC2 → Instances → Instance ID column.
```

Not good:
```
instance-id: i-03658657280f01308
```

**3. Explain why before asking the student to do anything**

Before showing a command or fix, tell the student why Kubernetes needs it.
One sentence is enough. The student should never be running a command they
do not understand the purpose of.

Good:
```
Why Kubernetes needs this (L1):
Kubernetes requires swap to be disabled. Without this, the kubelet will
refuse to start because swap undermines the memory guarantees Kubernetes
relies on for pod scheduling. We will explore this in the L1 kernel lesson.
```

Not good:
```
Run: sudo swapoff -a
```

**4. Name the ELS layer**

Every explanation should name which ELS layer it belongs to. This is not
bureaucracy — it is the primary teaching mechanism. The student is building
a mental model of where things live. Every piece of evidence should be
anchored to a layer.

**5. Distinguish "expected" from "broken"**

Many things that look wrong to a beginner are actually correct:
- Nodes showing NotReady before CNI is installed — correct
- kubelet showing inactive before kubeadm init — correct
- swapon --show producing no output — correct (swap is off)
- IMDSv2 returning nothing without a token — correct (not broken)

The coach must explicitly call these out as expected, not leave the student
wondering if something went wrong.

**6. Point forward, not just at the current state**

Where useful, tell the student what will change after the next step.
This builds anticipation and helps them verify their own work.

Good:
```
Save this output — compare it after Kubernetes and CNI are installed.
The differences show exactly what Kubernetes added to this node.
```

**7. Never talk down**

The coach explains things clearly because they are genuinely complex,
not because the student is slow. The tone is always:
"This is subtle and worth knowing" — never "this is obvious".

---

## What the coach is not

- Not a documentation generator — output should teach, not just describe
- Not a chatbot that answers questions — a coach that anticipates them
- Not a tool that assumes the student will figure it out — one that ensures they do
- Not a system that hides uncertainty — one that names it explicitly

---

## Application

These rules apply to:
- Shell script output (echo statements, section headers, inline comments)
- Streamlit UI text (captions, info boxes, why-this-matters explanations)
- Learning moment documents
- Testbed orientation docs
- Any text the student reads while using cka-coach
