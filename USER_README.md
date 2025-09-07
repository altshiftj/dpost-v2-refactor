# IPAT Data Watchdog - User Guide

## 🔬 What is IPAT Data Watchdog?

IPAT Data Watchdog is an automated data management system for scientific instruments. It monitors a designated folder on your computer, automatically processes new files from your laboratory device, organizes them properly, and uploads them to a secure database for long-term storage and collaboration.

> ### 🚨 CRITICAL FILE NAMING REQUIREMENT
> 
> **ALL FILES must follow this exact pattern:**
> 
> **`user-institute-sample_name.extension`**
> 
> **Example:** `jfi-ipat-polymer_test_001.tiff`
> 
> Files that don't follow this pattern will be moved to the "To_Rename" folder and won't be processed until renamed correctly.

### Key Benefits

- **🤖 Automated Processing**: No manual file organization required
- **📋 Data Validation**: Ensures files follow proper naming conventions
- **🗄️ Secure Storage**: Automatic backup to institutional database
- **📊 Session Management**: Groups related measurements together
- **🔍 Real-time Monitoring**: Live tracking of processing status
- **🚨 Error Handling**: Clear notifications when intervention is needed

## 🎯 Who Should Use This?

- **Laboratory Technicians** operating scientific instruments
- **Researchers** collecting data from automated devices
- **Data Managers** ensuring institutional data compliance
- **Students** working with laboratory equipment

## 🖥️ System Requirements

- **Operating System**: Windows 10 or later
- **Disk Space**: At least 1 GB free space
- **Network**: Internet connection for database synchronization
- **Permissions**: Administrator access for installation

## 🚀 Quick Start Guide

### Step 1: Installation

1. **Download the installer** for your specific device:
   - **SEM TischREM**: `wd-sem_phenomxl2.exe`
   - **PSA HoribaLinks**: `wd-psa_horibalinks_blb.exe`
   - **UTM Zwick**: `wd-utm_zwick.exe`

2. **Run the installer** as Administrator
3. **Follow the installation wizard** (typically installs to `C:\Watchdog\`)

### Step 2: Initial Setup

1. **Create your upload folder** (usually on Desktop):
   ```
   Desktop\Upload\
   ```

2. **Configure your device** to save files to this folder

3. **Start the service**:
   - Press `Windows + R`, type `services.msc`
   - Find "IPAT Data Watchdog" service
   - Right-click → Start

### Step 3: First Use

1. **Copy a test file** to your Upload folder
2. **Wait for processing** (usually 1-2 minutes)
3. **Check the Data folder** on your Desktop for organized files
4. **Review any error messages** if they appear

## 📁 Folder Structure

After installation, you'll see this folder structure on your Desktop:

```
Desktop/
├── Upload/           # 📥 DROP FILES HERE
├── Data/                    # 📊 Processed files appear here
│   ├── 2025-08-28/         # 📅 Daily folders
│   │   ├── record-001/     # 📋 Individual measurement records
│   │   │   ├── data.tiff   # 🖼️ Your processed files
│   │   │   └── metadata.json
│   │   └── record-002/
│   ├── 00_To_Rename/       # ⚠️ Files with naming issues
│   └── 01_Exceptions/      # 🚨 Files that couldn't be processed
```

### Folder Descriptions

| Folder | Purpose | What to Do |
|--------|---------|------------|
| `Upload` | **Input folder** - Place new files here | Configure your device to save here |
| `Data/YYYY-MM-DD/` | **Daily organized data** | Browse completed records |
| `00_To_Rename` | **Naming issues** | Rename files and move back to Upload |
| `01_Exceptions` | **Processing errors** | Check error logs, contact support |

## 🎛️ Using the System

### Normal Operation

1. **Configure your device** to save files to `Upload`
2. **Start your measurement** as usual
3. **Files are automatically processed** within minutes
4. **Check the daily Data folder** for organized results
5. **Files are automatically uploaded** to the institutional database

### File Naming Requirements

⚠️ **CRITICAL**: All files must follow the exact naming pattern: `usr-inst-sample_name`

**Required Format:** `user-institute-sample_name.extension`

- **user**: Your username or initials (3+ characters)
- **institute**: Institution/department code (3+ characters)  
- **sample_name**: Descriptive sample name (no spaces, use underscores)
- **extension**: File type (.tiff, .csv, .dat, etc.)

**Examples by Device:**

**SEM TischREM:**
- ✅ `jfw-ipat-polymer_sample_001.tiff`
- ✅ `abc-kit-steel_coating_test.tif`
- ✅ `xyz-iam-nanoparticle_analysis.tiff`

**PSA HoribaLinks:**
- ✅ `jfw-ipat-coating_experiment.csv`
- ✅ `def-kit-particle_size_batch2.dat`

**UTM Zwick:**
- ✅ `jfw-ipat-tensile_test_steel.txt`
- ✅ `ghi-iam-compression_polymer.csv`

**❌ INCORRECT Examples:**
- ❌ `sample.tiff` (missing user-institute prefix)
- ❌ `jfw-sample.tiff` (missing institute)
- ❌ `jfw-ipat sample.tiff` (spaces not allowed)
- ❌ `jfw..ipat-sample.tiff` (double separators)
- ❌ `ab-xy-sample.tiff` (user/institute too short)

### Session Management

The system automatically groups related files into **sessions**:

- **Session starts** when the first file arrives
- **Session continues** as long as files keep arriving (within 10 minutes)
- **Session ends** after 10 minutes of inactivity
- **Database upload** happens at session end

### Manual Session Control

Sometimes you may need manual control:

1. **Right-click the system tray icon** (if visible)
2. **Select "End Session Now"** to force immediate upload
3. **Or wait for automatic session timeout**

## 🔧 Configuration

### Environment Configuration

The system uses a `.env` file for configuration. Common settings:

```bash
# Device Selection
DEVICE_NAME=sem_phenomxl2

# Directory Paths (usually auto-configured)
WATCH_DIR=C:\Users\YourName\Desktop\Upload
DATA_DIR=C:\Users\YourName\Desktop\Data

# Session Settings
SESSION_TIMEOUT=600  # 10 minutes

# Database Settings (configured by admin)
KADI_SERVER=https://kadi.iam.kit.edu
KADI_TOKEN=your_access_token
```

### Device-Specific Settings

Each device has specific file handling rules:

**SEM TischREM (Electron Microscopy):**
- Accepts: `.tiff`, `.tif` files
- Special folders: `.odt`, `.elid` directories
- Session timeout: 10 minutes
- Auto-metadata extraction from TIFF headers

**PSA HoribaLinks (Particle Analysis):**
- Accepts: `.csv`, `.dat`, `.txt` files
- Session timeout: 5 minutes
- Automatic data validation and parsing

**UTM Zwick (Materials Testing):**
- Accepts: `.txt`, `.csv`, `.dat` files
- Session timeout: 15 minutes
- Force/displacement curve processing

## 🚨 Troubleshooting

### Common Issues

#### "Files Not Processing"

**Symptoms:** Files stay in Upload folder, nothing happens

**Solutions:**
1. **Check the service**: Windows Services → "IPAT Data Watchdog" → Restart
2. **Check file names**: Ensure they follow naming conventions
3. **Check permissions**: Ensure you can write to Desktop folders
4. **Check logs**: Look at `C:\Watchdog\logs\watchdog.log`

#### "Files Go to To_Rename Folder"

**Symptoms:** Files appear in `Desktop\Data\00_To_Rename\`

**Solutions:**
1. **Check naming pattern**: Files must follow `user-institute-sample_name.extension`
   - ✅ Correct: `jfw-ipat-sample_001.tiff`
   - ❌ Wrong: `sample.tiff` or `jfw-sample.tiff`
2. **Verify all three parts**: user (3+ chars), institute (3+ chars), sample_name
3. **Use underscores only**: Replace spaces with underscores in sample names
4. **Check separators**: Use single hyphens between user-institute, underscore in sample_name
5. **Rename and move back**: Fix the name and move to Upload folder

#### "Database Upload Fails"

**Symptoms:** Error dialogs about sync failures

**Solutions:**
1. **Check internet connection**
2. **Contact your system administrator** for database access
3. **Check authentication tokens** (if applicable)
4. **Try manual session end** from system tray

#### "System Tray Icon Missing"

**Symptoms:** Can't find the Watchdog icon

**Solutions:**
1. **Check service status**: Windows Services → "IPAT Data Watchdog"
2. **Restart the service**
3. **Check if running in background mode**

### Error Messages

| Error | Meaning | Solution |
|-------|---------|----------|
| "Invalid filename pattern" | File name doesn't follow `user-institute-sample_name` format | Rename file: `jfw-ipat-sample_name.ext` |
| "Unsupported file type" | File extension not allowed for this device | Check device settings for allowed types |
| "Session timeout" | No files for 10+ minutes | Normal behavior, session ended |
| "Database connection failed" | Network or authentication issue | Contact administrator |
| "Permission denied" | Can't access folders | Check folder permissions |

### Getting Help

#### Check System Status

**Health Dashboard:** http://localhost:8001/health
- View current system status
- Check if services are running

**Log Viewer:** http://localhost:8001/logs
- Real-time error messages
- Filter logs by keyword
- Download logs for support

**Metrics Dashboard:** http://localhost:8000/metrics
- Processing statistics
- Performance monitoring
- Session information

#### Contact Support

When contacting support, please provide:

1. **Device type** (SEM TischREM, PSA HoribaLinks, etc.)
2. **Error message** (exact text if possible)
3. **Log files** from `C:\Watchdog\logs\`
4. **Sample filenames** that are failing
5. **Steps to reproduce** the problem

## 📊 Monitoring Your Data

### Real-Time Status

The system provides several ways to monitor processing:

1. **System Tray Icon**: Shows processing status
2. **Desktop Folders**: Watch files move from Upload to Data
3. **Web Dashboard**: http://localhost:8001 for detailed status

### Processing Statistics

View processing metrics at http://localhost:8000/metrics:

- Files processed per session
- Processing time per file
- Error rates and types
- Session duration statistics

### Data Organization

Your processed data is organized for easy access:

```
Data/
├── 2025-08-28/              # Today's data
│   ├── record-001/          # First measurement of the day
│   │   ├── jfw-ipat-sample_A.tiff
│   │   ├── metadata.json
│   │   └── processing.log
│   ├── record-002/          # Second measurement
│   └── session-summary.json # Daily summary
├── 2025-08-27/              # Yesterday's data
└── archive/                 # Older data (auto-moved after 30 days)
```

### Database Integration

Your data is automatically uploaded to the institutional database:

- **Metadata** is extracted and catalogued
- **Files** are stored securely with backups
- **Search capability** allows future data discovery
- **Access control** ensures proper data sharing
- **Version history** tracks data changes

## 🔒 Data Security and Privacy

### Local Data Protection

- **Folder permissions** restrict access to authorized users
- **Service runs** under system account for security
- **Temporary files** are automatically cleaned up
- **Error logs** contain no sensitive data

### Database Security

- **Encrypted transmission** of all data to database
- **Authentication tokens** for secure access
- **Access logging** for audit trails
- **Backup systems** ensure data preservation

### Data Retention

- **Local files** are kept for 30 days by default
- **Database storage** follows institutional policies
- **Deletion requests** can be made through administrators
- **Archive policies** ensure long-term preservation

## 🔄 Updates and Maintenance

### Automatic Updates

- **Service updates** are deployed automatically
- **Configuration changes** may require restart
- **Database schema updates** are handled transparently

### Manual Maintenance

**Weekly:**
- Check error logs for recurring issues
- Verify disk space in Data folders
- Clean up old files in To_Rename folder

**Monthly:**
- Review processing statistics
- Update device-specific settings if needed
- Contact support for optimization recommendations

## 📋 Best Practices

### Best Practices

### File Management

1. **Follow the naming pattern**: Always use `user-institute-sample_name.extension`
   - Example: `jfw-ipat-experiment_day1.tiff`
2. **Use descriptive sample names**: `polymer_tensile_test_001` vs `test1`
3. **Use underscores for spaces**: `sample_name_here` not `sample name here`
4. **Keep names concise**: Aim for under 30 characters for the sample_name part
5. **Be consistent**: Use the same user-institute prefix for all your files

### Measurement Workflow

1. **Plan your session**: Group related measurements together
2. **Check file names**: Ensure proper naming before starting
3. **Monitor processing**: Watch for error messages
4. **Verify uploads**: Check database for successful sync
5. **Document experiments**: Add descriptions for important measurements

### Troubleshooting Workflow

1. **Check recent files**: Look in To_Rename and Exceptions folders
2. **Review error messages**: Check web dashboard for details
3. **Restart if needed**: Restart service for persistent issues
4. **Contact support early**: Don't wait for problems to accumulate

---

## 📞 Support Information

- **Technical Support**: [Your IT Support Contact]
- **System Administrator**: [Your Admin Contact]  
- **User Documentation**: This guide
- **Developer Documentation**: `DEVELOPER_README.md`

**Emergency Contact**: If the system is preventing critical work, contact your IT department immediately with error details and urgency level.

---

*This system is designed to make your scientific data management effortless. If you have suggestions for improvements or encounter any issues, please don't hesitate to reach out to the support team.*
