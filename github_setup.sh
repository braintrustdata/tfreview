#!/bin/bash

# GitHub Repository Setup Script for TFReview
# 
# Instructions:
# 1. First create a new repository on GitHub.com named "tfreview"
# 2. Replace YOUR_USERNAME below with your actual GitHub username
# 3. Run this script: bash github_setup.sh

# Replace this with your actual GitHub username
GITHUB_USERNAME="YOUR_USERNAME"

echo "🚀 Setting up GitHub repository for TFReview..."

# Add GitHub as remote origin
echo "📡 Adding GitHub remote..."
git remote add origin https://github.com/${GITHUB_USERNAME}/tfreview.git

# Rename master branch to main (GitHub's default)
echo "🔄 Renaming branch to main..."
git branch -M main

# Push code to GitHub
echo "⬆️ Pushing code to GitHub..."
git push -u origin main

echo "✅ Success! Your TFReview repository is now available at:"
echo "   https://github.com/${GITHUB_USERNAME}/tfreview"
echo ""
echo "🎉 Repository includes:"
echo "   • Complete Python package with CLI"
echo "   • Interactive HTML interface with improved UX"
echo "   • 5 sample Terraform plans for testing"
echo "   • Comprehensive test suite"
echo "   • Professional documentation"
echo "   • All recent improvements (grouped resources, floating progress, etc.)"