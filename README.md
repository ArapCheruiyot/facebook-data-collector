# 📊 Facebook Data Collector

A web application that extracts structured data from Facebook posts - including dates, locations, mentioned people, action types, and comments. Saves data directly to the user's computer (no server storage).

## ✨ Features

- **Paste any Facebook post** - Extracts date, location, people mentioned, and key quotes
- **Comment extraction** - Captures comments with sentiment analysis (positive/neutral/negative)
- **Action detection** - Automatically categorizes posts (roads, water, funeral, church, fundraising, etc.)
- **Custom keywords** - Users can add/remove keywords to customize action detection
- **Local storage** - Data saves to CSV files on your own computer (privacy first)
- **Export to CSV** - Download your data as CSV files
- **Statistics dashboard** - Shows post counts and action breakdowns

## 🚀 How to Use

1. **Select a folder** - Click "Select Save Folder" and choose where to save your data
2. **Paste a Facebook post** - Copy any Facebook post and paste it into the text area
3. **Click Save** - The app extracts data and saves it to CSV files in your selected folder
4. **Manage keywords** - Add or remove keywords to control what actions are detected
5. **Export data** - Download your posts and comments as CSV files

## 🛠️ Technical Stack

- **Backend**: Python, Flask
- **Storage**: Local CSV files (user's computer)
- **Extraction**: Regex patterns, NLP
- **Frontend**: HTML, CSS, JavaScript

## 📁 File Structure

When you save posts, two CSV files are created in your selected folder:

- `raymond_posts.csv` - All extracted post data
- `raymond_comments.csv` - All extracted comments

## 🔒 Privacy

- **No server storage** - Your data never leaves your computer
- **Each user's data is private** - Different users save to different folders
- **You control everything** - You choose where to save your data

## 🌐 Live Demo



## 👨‍💻 Author

Moses Kipkorir Cheruiyot

## 📄 License

MIT
