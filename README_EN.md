# Newspaper Job Advertisement Block Extraction System

<p>
  <img src="https://img.shields.io/badge/Docker-Ready-blue?logo=docker" alt="Docker Ready" />
  <img src="https://img.shields.io/badge/Python-3.11+-green?logo=python" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/AI-Gemini%202.0-orange?logo=google" alt="AI Gemini 2.0" />
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="License MIT" />
</p>

## 🎯 Project Overview

An intelligent newspaper job advertisement extraction system that automatically extracts job advertisement blocks from scanned newspaper images and analyzes job information using AI technology. The system is fully Dockerized, supports one-click deployment, and is suitable for 24/7 production environment operation.

## ✨ Core Features

### 🔧 Image Processing
- **Multi-format Support**: JPG, PNG, multi-page PDF files
- **Smart Block Detection**: Precise job advertisement block segmentation using OpenCV
- **Automatic Orientation Correction**: AI detects image orientation and auto-rotates
- **Efficient Processing**: Memory optimized, uses only 5MB memory when processing large files

### 🤖 AI Analysis
- **Smart Recognition**: Uses Google Gemini 2.0 model to analyze job content
- **Structured Data**: Automatically extracts position, salary, location, contact information, etc.
- **Industry Classification**: Automatically categorizes into 19 standard industry categories
- **Parallel Processing**: Supports multi-threaded AI analysis for improved processing speed

### 🌐 Web Interface
- **Real-time Progress**: Detailed processing progress display (Upload → Processing → AI Analysis)
- **Result Preview**: Grid layout displaying all extracted blocks
- **Multi-format Download**: One-click download of CSV, SQL, images, description files
- **Google Sheets Integration**: One-click creation and data sending to spreadsheets

### 🐳 Docker Deployment
- **One-click Start**: Complete containerized solution
- **Production Ready**: Includes health checks, auto-restart, log management
- **Security Configuration**: Non-root user, resource limits, security options
- **Auto Cleanup**: 4-hour automatic cleanup mechanism, supports long-term operation

## 🚀 Quick Start

### Docker Deployment (Recommended)

1. **Environment Check**
   ```bash
   # Windows
   .\docker-check.bat
   
   # Linux/macOS
   docker --version && docker-compose --version
   ```

2. **One-click Start**
   ```bash
   # Windows
   .\docker-start.bat
   
   # Linux/macOS
   chmod +x docker-start.sh && ./docker-start.sh
   ```

3. **Access Application**
   - Main page: http://localhost:8080
   - Health check: http://localhost:8080/health
  
For detailed Docker deployment instructions, please refer to [README-Docker.md](docs/README-Docker.md)

### Local Development Environment

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables
cp env.example .env
# Edit .env file, add your Gemini API key

# 3. Start application
python app.py
```

## 🖼️ Processing Results Demo

### Original Newspaper
<div align="center">
  <img src="newspaper/newspaper1.jpg" alt="Original Newspaper" width="400" />
</div>

### Extracted Job Advertisement Blocks
<div align="center" style="display: flex; gap: 10px; justify-content: center;">
  <img src="newspaper/newspaper1.jpg_blocks/239_954_927_1513.jpg" alt="Job Block 1" width="200" />
  <img src="newspaper/newspaper1.jpg_blocks/929_971_1615_1527.jpg" alt="Job Block 2" width="200" />
  <img src="newspaper/newspaper1.jpg_blocks/1618_2084_2284_2360.jpg" alt="Job Block 3" width="200" />
</div>

## 📊 AI Analysis Results

The system automatically extracts the following information:
- **Job Position**: Job title and occupation type
- **Industry Classification**: Automatic categorization into 19 standard industry categories
- **Work Conditions**: Working hours, salary benefits
- **Geographic Information**: Work location, service area
- **Contact Information**: Phone, address, other contact methods
- **Additional Information**: Job requirements, benefits, remarks

## 📥 Download & Integration

### Download Formats
- **CSV Table**: Structured data that can be directly opened in Excel
- **SQL Database**: Complete table creation and insert statements
- **Image Files**: All extracted job block images
- **AI Descriptions**: Detailed text analysis results

### 🔗 Google Sheets Auto Integration

#### Quick Usage
1. After image processing is complete, click "Create Google Sheets" on the results page
2. System automatically creates a new spreadsheet and imports all job data
3. Provides direct link for one-click access to Google Sheets

#### Spreadsheet Content
- **Job Data Worksheet**: Contains complete information including jobs, industries, salaries, locations
- **Processing Summary Worksheet**: Shows processing statistics and industry distribution
- **Auto Formatting**: Header row styles, colors, and borders
- **Permission Settings**: Automatically set to "Anyone with the link can view"

#### Custom Google Apps Script (Optional)

If you want to use your own Google Apps Script:

1. **Create Apps Script Project**
   - Go to [Google Apps Script](https://script.google.com/)
   - Create new project, copy content from `google_apps_script.js`

2. **Deploy as Web Application**
   - Select "Deploy" → "New Deployment" → "Web Application"
   - Execute as: Me, Access: Anyone
   - Copy the web application URL

3. **Use in System**
   - Expand "Custom Google Apps Script URL" option on results page
   - Enter your URL and create

#### Data Format
| Field | Description | Example |
|-------|-------------|---------|
| Job | Job title | Software Engineer |
| Industry | Industry category | Information Technology |
| Time | Working hours | Monday to Friday 9:00-18:00 |
| Salary | Salary benefits | Monthly salary 50,000-70,000 TWD |
| Location | Work location | Xinyi District, Taipei |
| Contact | Contact information | 02-1234-5678 |
| Other | Other information | Python experience required |
| Source Image | Source filename | job_block_1.jpg |
| Page Number | PDF page number | 1 |

## 🔧 Configuration Options

### Environment Variables
```bash
# Required configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Optional configuration
FLASK_ENV=production
FLASK_HOST=0.0.0.0
FLASK_PORT=8080
MAX_CONTENT_LENGTH=16777216
```

### Processing Parameters
- **Auto Orientation Correction**: Enable/disable image orientation detection
- **Parallel Processing**: Enable/disable multi-threaded AI analysis
- **Debug Mode**: Save intermediate images of processing steps

## 📋 System Requirements

- **Docker**: 20.10+ (recommended)
- **Docker Compose**: 1.29+
- **Memory**: Minimum 1GB, recommended 2GB
- **Storage**: Minimum 5GB available space
- **Network**: Internet connection required for AI functionality

## 🛠️ Management and Monitoring

### Basic Commands
```bash
# Basic operations
docker-compose ps                # Check status
docker-compose logs -f           # View logs
docker-compose down              # Stop services
docker-compose restart          # Restart services

# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# Automated testing
.\docker-test.bat               # Windows complete test

# Manual cleanup
docker system prune -a          # Clean Docker resources
```

### Monitoring Interface
- `/health` - Application health status
- `/admin/storage` - View storage usage
- `/admin/cleanup` - Manual cleanup execution

### Auto Cleanup
- Automatically clean old files every 4 hours
- Clean files older than 4 hours on startup
- Support manual cleanup and status monitoring

## 🔒 Security Features

- **Container Security**: Non-root user execution
- **Resource Limits**: CPU and memory usage limits
- **Network Isolation**: Independent Docker network
- **File Permissions**: Appropriate file system permissions

## 🤝 Technical Support

### Common Issues
1. **Port Conflicts**: Modify port mapping in docker-compose.yml
2. **Insufficient Memory**: Adjust Docker resource allocation
3. **API Quota**: Check Gemini API usage limits
4. **Google Sheets Issues**: Check network connection and API status

### Troubleshooting
```bash
# Check container status
docker-compose ps

# View detailed logs
docker-compose logs --tail=50 newspaper-extractor

# Rebuild images
docker-compose build --no-cache
```

## 📈 Performance Metrics

- **Processing Speed**: Single newspaper page < 30 seconds
- **Memory Usage**: Only 5MB when processing large files
- **Concurrent Support**: Supports multiple users simultaneously
- **Availability**: 24/7 operation capability

## 🎯 Use Cases

- **News Media**: Historical newspaper digitization
- **Human Resources**: Job market analysis
- **Academic Research**: Employment trend studies
- **Data Collection**: Large-scale job information gathering

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

<div align="center">
  <p>⭐ If this project helps you, please give us a star!</p>
  <p>🐛 Found an issue? Feel free to submit an Issue or Pull Request</p>
</div> 