# Cloud-Cost & Infrastructure Optimizer

A tool that statically analyses a IaC file using an AI Agent and provides a comprehensive report highlighting security vulnerabilities, cost optimisations and more. Compatible with Docker, Terraform and AWS. 

## ✨ Features
- **Fast & Easy** - Simply drag and drop the file to kick start the analysis
- **Detailed Analysis** - Uses an DevOps Agent to analyse each line
- **Production Readiness** - Provides a corrected template which is production ready
- **Project Spaces** - Organise your workspace into seperate projects

## 🚀 Quick Start

### Prerequisites
- Node v24+
- npm v11+
- python 3+
- OpenAPI key

### Installation

1. Clone the repository
```bash
git clone https://github.com/BVSanthosh/Cloud-Cost-and-Infrastructure-Optimizer.git
cd Cloud-Cost-and-Infrastructure-Optimizer
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