# 🚀 Pygame Revision App with Gemini API

Welcome to our EdTech revision tool! This project was built in 24 hours for a hackathon, blending a fast-paced Pygame "shoot-and-revise" game loop with live Gemini API integration to generate dynamic learning questions on the fly.

The application launches with an interactive HTML/CSS/JS front-end landing page, which connects seamlessly to a Python backend server running locally on your machine.

---

## 🎮 How to Setup and Play Locally

Follow these step-by-step instructions to clone, configure, and launch the game on your own computer.

### 📋 Prerequisites

Before you begin, ensure you have the following installed on your system:

* **Python 3.13** (Crucial: The codebase expects version 3.13 to function correctly). You can download it from [python.org](https://www.python.org/downloads/), scroll down to find python 3.13 and install it. During installation, make sure to check the box that says **"Add Python to PATH"**.

---

## 🛠️ Step-by-Step Installation

### 1. Download the Repository

Choose one of the following methods to get the files onto your machine:

* **Option A (Via Terminal):** Clone the repository using Git:
```bash
git clone https://github.com/dean-8/Hackathon_repo.git

```


* **Option B (Direct Download):** Click the green **Code** button at the top right of this GitHub page, select **Download ZIP**, and extract the contents to a folder of your choice.

### 2. Open the Project Directory

Open your terminal (Command Prompt, PowerShell, or your built-in VS Code terminal) and navigate into the project folder:

```bash
cd Hackathon_repo

```

### 3. Install Required Dependencies

Run the following command to install the required Python packages (`pygame` for the core game mechanics and `google-genai` for the AI features):

```bash
pip install pygame google-genai

```

---

## 🔑 4. Configuring Your Gemini API Key

This game relies on Google Gemini AI to dynamically generate and tailor educational revision questions while you play. To use this feature, you must generate a free API key from Google and provide it to the game server.

### 📡 Part A: How to Get a Free API Key

1. Go to **[Google AI Studio](https://aistudio.google.com/)** and log in with your standard Google/Gmail account.
2. In the top-left sidebar, click the blue **Get API key** button.
3. Click the **Create API key** button at the top right.
4. A popup window will appear:
* Select **Create API key in a new project** (or pick an existing Google Cloud project if you have one).


5. Once generated, click the **Copy** button next to the long string of characters. This string is your unique access key.

> ⚠️ **Security Warning:** Treat your API key like a password. Never paste it directly into your code files, and never upload it to GitHub, or others could steal your Google account API quota.

---

### 💻 Part B: How to Apply the Key to Your System

The game is programmed to look for your key inside your computer's temporary environment variables. Before you start the application, you must load your key into your active terminal session using one of the commands below.

Choose the box that matches the terminal or Operating System you are currently running:

#### 🔹 Option 1: Windows (PowerShell) - *Recommended for VS Code users*

If you are running your terminal directly inside VS Code on Windows, you are likely using PowerShell. Run this command:

```powershell
$env:GEMINI_API_KEY="your_actual_api_key_here"

```

#### 🔹 Option 2: Windows (Command Prompt / CMD)

If you opened a standard Windows Command Prompt window, run this command:

```cmd
set GEMINI_API_KEY="your_actual_api_key_here"

```

#### 🔹 Option 3: Mac / Linux

If you are on a macOS or Linux machine, run this command:

```bash
export GEMINI_API_KEY="your_actual_api_key_here"

```

*(Note: Replace `your_actual_api_key_here` with the long string of characters you copied from Google AI Studio, keeping the quotation marks).*

---

### 🔍 Part C: How to Verify It's Working

If you want to double-check that your terminal successfully saved your key before you try launching the game, run this command to print it:

* **Windows (PowerShell):** `echo $env:GEMINI_API_KEY`
* **Windows (CMD):** `echo %GEMINI_API_KEY%`
* **Mac / Linux:** `echo $GEMINI_API_KEY`

If it prints your key back out to you, you are ready to move on to Step 5 and launch the game server!



---

## 🕹️ 5. Running the Program

Once your dependencies are installed and your API key is set in the terminal session, kick off the local Python web server by running:

```bash
python launch.py

```

> 💡 **Note:** Running this file will spin up the backend server and automatically open up your default browser to launch the HTML landing page. From there, you're ready to start playing!

---

## 👥 Tech Stack & Contributors

* **Front-End:** HTML5, CSS3, JavaScript
* **Back-End:** Python 3.13, Gemini API (`google-genai`)
* **Game Engine:** Pygame
* **Developed by:** Built collaboratively as a team hackathon submission.
