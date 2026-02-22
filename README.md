# Web 2 Shell 🌐➡️👨‍💻
Have you ever wonder,
``` 
is it possible for an attacker to remotely control 
my computer because I simply click a perfectly normal website? 
```
This project will answer that question.

![[web2shell-thumbnail.png]]
---
# What is Web 2 Shell
Web 2 Shell is a study case project meant to study a scenario where an attacker can take control another user's computer just because they open a perfectly normal website. 

---
# Expected Scenario flow
- An attacker crafts a perfectly normal website
- At the backend, a reverse shell payload is embedded
- the website is published and the user clicks it
- when the time a user enters the website, the payload will be executed and stored as cache in the user's computer for persistence

# Lab setup (may be vary)
The core setup for this case study is basically **ONE** server and **TWO** computers or virtual machines that are using different operating systems. Different operating systems can help us to understand browser behaviors on different OS. 

## My Personal LAB Setup
### Computer environment
- Oracle Virtualbox ( VMware workstation is also fine)
- 1 Ubuntu desktop VM
- 1 Debian 13 desktop VM
- 1 Windows 11 computer
### Software 
- Code Editor (I use Visual Studio Code personally)
- Web browser (Firefox, Edge, Chrome)
- Python3-venv, python3-pip
  
# Installation Steps
1. ```git clone https://www.github.com/NotReallySerious/WEB-2-SHELL```
2. ```cd WEB-2-SHELL```
3. ```python3 -m venv venv```
4. ```pip3 install -r requirements.txt```
5. Run both the listener and the website's backend
```python3 app.py```
```python3 listener.py```
