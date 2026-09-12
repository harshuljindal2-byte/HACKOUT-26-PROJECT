# ⚡ AeroSolar: AI Predictive Maintenance & Fleet Intelligence

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Google Gemini API](https://img.shields.io/badge/AI-Google%20Gemini%20API-4285F4?logo=google&logoColor=white)](https://ai.google.dev/)
[![HackOut'26](https://img.shields.io/badge/Hackathon-HackOut'26-orange)](#)

> **Live Web App: **https://aerosolar.streamlit.app/** (Deployed on Streamlit Community Cloud)*  
> **HackOut'26 Theme:** Renewable Energy Intelligence  
> **Problem Statement:** Predictive Maintenance for Solar & Wind Assets  
> **Target Users:** Solar/Wind Farm Operators, Field Technicians, Asset Owners  

---

## 📌 Problem Statement & Industry Context

Solar PV arrays and wind turbines operate continuously outdoors under harsh environmental conditions—dust accumulation, thermal stress, violent wind gusts, and mechanical vibration. Over time, minor operational anomalies (such as panel soiling, elevated gearbox temperatures, subtle bearing friction, or voltage drops) silently escalate into major equipment breakdowns.

In the renewable energy industry today, operations and maintenance (O&M) remain largely **reactive**:
1. **Late Detection**: Equipment issues are caught only after physical breakdown or severe power loss occurs.
2. **Costly Manual Inspections**: Routine manual checks across sprawling solar fields and remote wind farms are slow, expensive, and impractical to run frequently.
3. **Inefficient Technician Dispatch**: Field teams often travel long distances to inspect healthy assets while unnoticed micro-faults quietly worsen elsewhere.

$$\text{Unnoticed Fault} \longrightarrow \text{Equipment Failure} \longrightarrow \text{Generation Loss (kWh)} \longrightarrow \text{Direct Revenue Loss}$$

---

## 💡 Proposed Solution

**AeroSolar** is a cloud-native, AI-powered predictive maintenance and fleet intelligence platform for solar arrays and wind turbines. It continuously monitors simulated IoT telemetry streams to catch structural and electrical anomalies before equipment failure happens.

Rather than flooding operators with raw numbers or false alerts, the system provides:
* **Root-Cause Diagnostics**: Distinguishes between solar panel soiling hotspots and wind turbine bearing friction.
* **Automated Health Scoring**: Tags assets instantly as **NORMAL** (Green), **WARNING** (Yellow), or **CRITICAL** (Red).
* **Weather False-Alarm Suppression**: Cross-references ambient weather conditions (e.g., wind gusts) against internal mechanical sensors to eliminate false alarms.
* **Monetary Loss Quantification**: Translates physical efficiency degradation directly into daily energy loss ($\text{kWh}$) and financial revenue risk.
* **AI-Generated Technician Work Orders**: Leverages the **AI LLM** to output 2-sentence root-cause diagnostics and step-by-step repair checklists.

---

## ✨ Key Features

- 🌐 **Free Public Web Access**: Hosted 24/7 on **Streamlit Community Cloud** with zero installation required.
- 📊 **Simulated Real-Time Telemetry Stream**: Monitors solar panel temperature (°C), soiling rate (%), voltage (V), current (A), and wind turbine vibration (Hz), gearbox temperature (°C), oil pressure (bar), and power output (kW).
- 🟢 **Automated Fleet Health Scoring**: Classifies asset health into clear **NORMAL**, **WARNING**, and **CRITICAL** operational states.
- 🌪️ **Weather False-Alarm Filter**: Suppresses false alerts when high turbine vibration is caused purely by temporary wind gusts rather than internal gearbox failure.
- 🤖 **AI Root-Cause Analysis**: Uses Generative AI to deliver instant, plain-language failure explanations and technician repair guides.
- 💰 **Financial Impact Estimator**: Calculates daily lost generation ($\text{kWh}$) and revenue risk (₹) based on asset capacity and electricity tariffs.
- 🎛️ **Interactive Live Fault Inserter**: Features sidebar controls that allow judges to inject synthetic faults live during demonstrations.

---

## 🌐 Deploying & Hosting on Streamlit Community Cloud

This repository is optimized for **1-click continuous deployment** on **Streamlit Community Cloud**.

### **Step 1: Repository Structure Check**
Ensure your GitHub repository has the following files in the root folder:
```text
aerosolar/
├── app.py                     # Main Streamlit application
├── requirements.txt           # Package dependencies
├── README.md                  # Project documentation
├── .gitignore                 # Excludes cache and secret files
└── docs/
    └── Project_Proposal.pdf   # HackOut'26 proposal document
```

### **Step 2: Streamlit `requirements.txt` File**
Streamlit Community Cloud automatically reads `requirements.txt` to install all necessary Python libraries during build:
```text
streamlit
pandas
numpy
plotly
google-generativeai
python-dotenv
```

### **Step 3: Deploying via Streamlit Cloud Portal**
1. Sign in to **[share.streamlit.io](https://share.streamlit.io)** using your **GitHub account**.
2. Click the **"New app"** button.
3. Select your repository (`username/aerosolar`), branch (`main`), and set the main file path to **`app.py`**.
4. Choose a custom public URL (e.g., `aerosolar.streamlit.app`).

### **Step 4: Managing Secrets (Google Gemini API Key)**
To securely provide the Gemini API key without exposing it in public GitHub code:
1. Before clicking Deploy, click **"Advanced settings..."** (or open **Settings ⚙️ -> Secrets** on your deployed app dashboard).
2. Paste your Google Gemini API key in **TOML format**:
   ```toml
   GEMINI_API_KEY = "-------------------------"
   ```
3. Click **Save** and **Deploy!**

> **Note on API Key Handling in Code**: The application automatically checks both `st.secrets["GEMINI_API_KEY"]` (for Streamlit Community Cloud) and `.env` / `os.getenv("GEMINI_API_KEY")` (for local development).

---

## 🏗️ System Architecture & Workflow

```text
+-----------------------------------------------------------------------------------+
| 1. TELEMETRY DATA SIMULATOR (Python, Pandas, NumPy)                               |
|    - Generates multi-modal streams: Solar (soiling, temp, I, V) & Wind (vibe, temp)|
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| 2. SMART ANOMALY DETECTION & FALSE-ALARM FILTER                                   |
|    - Threshold checking (NORMAL / WARNING / CRITICAL)                             |
|    - Suppresses alerts if high vibration is due to external wind gusts             |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| 3. AI DIAGNOSTICS & FINANCIAL LOSS ENGINE                                         |
|    - Revenue Math: Daily Generation Loss (kWh) & Revenue Loss (₹)                 |
|    - Google Gemini LLM API: Generates root-cause summary & technician work order |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| 4. STREAMLIT COMMUNITY CLOUD DASHBOARD                                            |
|    - Live fleet management, Plotly telemetry charts, and fault injection controls |
+-----------------------------------------------------------------------------------+
```

---

## 🛠️ Technology Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Web Dashboard** | Streamlit | Pure Python framework for live fleet UI & demo controls |
| **Cloud Hosting** | Streamlit Community Cloud | Free, shareable public web link for judges |
| **Data Generator** | Pandas, NumPy | Simulates real-time IoT sensor telemetry streams |
| **AI Engine** | Google Gemini API | Generates natural-language root cause diagnostics |
| **Visualizations** | Plotly Express | Interactive real-time telemetry graphs |
| **Secrets Manager** | Streamlit Secrets / `python-dotenv` | Secure API key management |

---

## 💻 Local Development Setup:

If you wish to clone and run the app locally on your computer:

```bash
# 1. Clone the repository
git clone ----------------------------
cd --------------------

# 2. Install required packages
pip install -r requirements.txt

# 3. Create a .env file with your API key
echo "GEMINI_API_KEY= ---------------------" > .env

# 4. Run the Streamlit app
streamlit run app.py
```

Open `http://localhost:8501` in your web browser.

---

## 👥 Team & Submission Info

- **Hackathon:** HackOut'26
- **Theme:** Renewable Energy Intelligence
- **Project Name:** AeroSolar
- **Target Audience:** Solar & Wind Farm Operators, Asset Owners, Field Technicians
