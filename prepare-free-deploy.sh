#!/bin/bash

# ============================================
# PREPARE FOR FREE DEPLOYMENT
# Helps you get ready for Render/Railway/Fly.io
# ============================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔════════════════════════════════════════╗"
echo "║  RickQueue FREE Deployment Prep Tool  ║"
echo "╚════════════════════════════════════════╝"
echo -e "${NC}"

print_step() {
    echo -e "\n${BLUE}→${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check git
print_step "Step 1: Checking Git Setup"

if ! command -v git &> /dev/null; then
    print_error "Git not installed!"
    echo "Install from: https://git-scm.com/"
    exit 1
fi

if [ ! -d .git ]; then
    print_warning "Git not initialized"
    read -p "Initialize git? (y/n): " init_git
    if [ "$init_git" = "y" ]; then
        git init
        git add .
        git commit -m "Initial commit - RickQueue MVP"
        print_success "Git initialized"
    fi
else
    print_success "Git initialized"
fi

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    print_warning "You have uncommitted changes"
    read -p "Commit now? (y/n): " commit_now
    if [ "$commit_now" = "y" ]; then
        git add .
        read -p "Commit message: " commit_msg
        git commit -m "$commit_msg"
        print_success "Changes committed"
    fi
fi

# Check Firebase credentials
print_step "Step 2: Checking Firebase Credentials"

if [ -f firebase-credentials.json ]; then
    print_success "Firebase credentials found"
    
    # Convert to base64 for environment variable
    print_step "Converting to base64 for deployment..."
    
    if command -v base64 &> /dev/null; then
        cat firebase-credentials.json | base64 > firebase-base64.txt
        print_success "Base64 version saved to: firebase-base64.txt"
        echo ""
        echo -e "${YELLOW}IMPORTANT:${NC} Copy this for deployment:"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        head -c 100 firebase-base64.txt
        echo "... (truncated)"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo "Full content in: firebase-base64.txt"
    fi
else
    print_error "firebase-credentials.json not found!"
    echo ""
    echo "Get it from Firebase Console:"
    echo "1. Go to https://console.firebase.google.com"
    echo "2. Select your project"
    echo "3. Settings → Service Accounts"
    echo "4. Generate New Private Key"
    echo "5. Save as firebase-credentials.json in project root"
    exit 1
fi

# Check .env file
print_step "Step 3: Checking Environment Configuration"

if [ ! -f .env ]; then
    print_warning ".env not found, creating from template"
    cp .env.example .env
    print_success ".env created"
fi

# Check if .gitignore includes secrets
print_step "Step 4: Checking .gitignore"

if [ -f .gitignore ]; then
    if grep -q "firebase-credentials.json" .gitignore; then
        print_success "Firebase credentials in .gitignore ✓"
    else
        echo "firebase-credentials.json" >> .gitignore
        print_warning "Added firebase-credentials.json to .gitignore"
    fi
    
    if grep -q ".env" .gitignore; then
        print_success ".env in .gitignore ✓"
    else
        echo ".env" >> .gitignore
        print_warning "Added .env to .gitignore"
    fi
else
    print_error ".gitignore not found!"
    cat > .gitignore << 'EOF'
# Environment
.env
firebase-credentials.json
firebase-base64.txt

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
venv/
env/

# Logs
logs/
*.log

# Database
*.db
*.sqlite

# IDE
.vscode/
.idea/
*.swp
EOF
    print_success "Created .gitignore"
fi

# Check deployment configs
print_step "Step 5: Checking Deployment Configurations"

if [ -f render.yaml ]; then
    print_success "render.yaml found (for Render deployment)"
else
    print_warning "render.yaml not found"
    echo "This is needed for Render deployment"
fi

if [ -f railway.json ]; then
    print_success "railway.json found (for Railway deployment)"
else
    print_warning "railway.json not found (optional)"
fi

# Create GitHub repo
print_step "Step 6: GitHub Repository"

REMOTE_URL=$(git config --get remote.origin.url 2>/dev/null || echo "")

if [ -z "$REMOTE_URL" ]; then
    print_warning "No GitHub remote configured"
    echo ""
    echo "To deploy, you need to push to GitHub first:"
    echo ""
    echo "1. Create new repo on GitHub: https://github.com/new"
    echo "2. Run these commands:"
    echo ""
    echo -e "${GREEN}git remote add origin https://github.com/YOUR_USERNAME/rickqueue-backend.git"
    echo "git branch -M main"
    echo "git push -u origin main${NC}"
    echo ""
else
    print_success "GitHub remote: $REMOTE_URL"
    
    read -p "Push to GitHub now? (y/n): " push_now
    if [ "$push_now" = "y" ]; then
        git push origin main || git push -u origin main
        print_success "Pushed to GitHub"
    fi
fi

# Summary
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ PREPARATION COMPLETE!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}📋 DEPLOYMENT CHECKLIST:${NC}"
echo ""

if [ -d .git ]; then
    echo "✓ Git initialized"
else
    echo "✗ Git not initialized"
fi

if [ -z "$(git status --porcelain)" ]; then
    echo "✓ No uncommitted changes"
else
    echo "⚠ Uncommitted changes exist"
fi

if [ -f firebase-credentials.json ]; then
    echo "✓ Firebase credentials present"
else
    echo "✗ Firebase credentials missing"
fi

if [ -f firebase-base64.txt ]; then
    echo "✓ Base64 credentials ready"
else
    echo "⚠ Base64 credentials not generated"
fi

if [ ! -z "$REMOTE_URL" ]; then
    echo "✓ GitHub remote configured"
else
    echo "⚠ GitHub remote not configured"
fi

echo ""
echo -e "${BLUE}🚀 NEXT STEPS:${NC}"
echo ""
echo "Choose your FREE deployment platform:"
echo ""
echo "1️⃣  RENDER.COM (Recommended)"
echo "   → 100% FREE for 90 days"
echo "   → Go to: https://render.com"
echo "   → New → Blueprint → Connect GitHub"
echo ""
echo "2️⃣  RAILWAY.APP"
echo "   → $5 free credit/month"
echo "   → Run: npm i -g @railway/cli && railway login"
echo ""
echo "3️⃣  FLY.IO"
echo "   → Always-on free tier"
echo "   → Run: curl -L https://fly.io/install.sh | sh"
echo ""
echo -e "${YELLOW}📖 See FREE_DEPLOYMENT.md for detailed instructions${NC}"
echo ""

# Offer to open documentation
if command -v open &> /dev/null; then
    read -p "Open deployment guide? (y/n): " open_docs
    if [ "$open_docs" = "y" ]; then
        if [ -f "FREE_DEPLOYMENT.md" ]; then
            open FREE_DEPLOYMENT.md
        else
            echo "FREE_DEPLOYMENT.md not found in current directory"
        fi
    fi
fi

echo ""
echo -e "${GREEN}Good luck with your deployment! 🚀${NC}"
echo ""