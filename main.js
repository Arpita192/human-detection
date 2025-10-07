const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');
const csv = require('csv-parser');

let mainWindow;
let pythonProcess;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false,
            preload: path.join(__dirname, 'preload.js')
        },
        icon: path.join(__dirname, 'icon.png')
    });
    
    const preloadPath = path.join(__dirname, 'preload.js');
    if (!fs.existsSync(preloadPath)) {
        fs.writeFileSync(preloadPath, '');
    }

    mainWindow.loadFile('index.html');

    mainWindow.on('closed', () => {
        mainWindow = null;
        if (pythonProcess) {
            pythonProcess.kill();
        }
    });
}

app.on('ready', createWindow);

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (mainWindow === null) {
        createWindow();
    }
});

// --- IPC Handlers ---

ipcMain.on('start-detection', (event) => {
    if (pythonProcess) {
        return; 
    }
    pythonProcess = spawn('python', ['human_detection.py']);

    let scriptOutputBuffer = '';
    pythonProcess.stdout.on('data', (data) => {
        scriptOutputBuffer += data.toString();
        let newlineIndex;
        while ((newlineIndex = scriptOutputBuffer.indexOf('\n')) !== -1) {
            const completeLine = scriptOutputBuffer.substring(0, newlineIndex).trim();
            scriptOutputBuffer = scriptOutputBuffer.substring(newlineIndex + 1);
            if (completeLine) {
                mainWindow.webContents.send('python-data', completeLine);
            }
        }
    });

    pythonProcess.stderr.on('data', (data) => {
        mainWindow.webContents.send('python-error', data.toString());
    });

    pythonProcess.on('close', (code) => {
        mainWindow.webContents.send('python-error', `Python script exited with code ${code}`);
        pythonProcess = null;
    });
});

ipcMain.on('stop-detection', (event) => {
    if (pythonProcess) {
        // --- MODIFIED LOGIC ---
        // Instead of sending a signal, we write a command to the script's standard input.
        // This is a more reliable way to ask the script to shut down gracefully.
        pythonProcess.stdin.write('QUIT\n');
        pythonProcess = null;
    }
});

ipcMain.on('read-log-file', (event) => {
    const results = [];
    const logFilePath = 'log_report.csv';

    if (!fs.existsSync(logFilePath)) {
        event.reply('log-file-data', []);
        return;
    }

    fs.createReadStream(logFilePath)
        .pipe(csv())
        .on('data', (data) => results.push(data))
        .on('end', () => {
            event.reply('log-file-data', results.reverse());
        });
});

