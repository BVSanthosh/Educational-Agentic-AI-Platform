# Educational Agentic AI Platform

A educational hub containing a collection of tools for enhancing how people approach learning and researching

## ✨ Features
- **Document Summarization** - Uplaod a file and recieve a concise summary
- **Reference Generation** - Receive a list of references (links to articles, blog posts, research papers and etc.) based on a specified topic
- **Deep Research & Report Writing** - Receive a detailed research report based on a specificed subjet matter

## 🚀 Quick Start

### Prerequisites
- Node v24+
- npm v11+
- Python 3+
- OpenAPI key

### Installation

1. Clone the repository
```bash
git clone https://github.com/BVSanthosh/Educational-Agentic-AI-Platform.git
cd Educational-Agentic-AI-Platform
```

2. Backend Installation & Setup
```bash
# Navigate to backend root
cd backend

# Create the virtual environment
python -m venv .venv

# Activate the virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows (Command Prompt):
.venv\Scripts\activate
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1

# Install dependency manifest
pip install -r requirements.txt

# Copy environment variables 
cp .env.example .env

# Run the server
fastapi dev
```

3. Frontend Installation & Setup
```bash
# Navigate to the frontend root
cd frontend

# Install React dependencies
npm install

# Copy environment variables 
cp .env.example .env

# Start development server
npm run dev
```