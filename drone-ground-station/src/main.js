const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1100,
    minHeight: 700,
    backgroundColor: '#1a1a2e',
    title: 'Drone Ground Station',
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      enableRemoteModule: true
    },
    show: false
  });

  mainWindow.loadFile(path.join(__dirname, 'index.html'));

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// IPC: List serial ports
ipcMain.handle('list-ports', async () => {
  try {
    const { SerialPort } = require('serialport');
    const ports = await SerialPort.list();
    return ports;
  } catch (err) {
    return [];
  }
});

// IPC: Save mission to file
ipcMain.handle('save-mission', async (event, missionData) => {
  const result = await dialog.showSaveDialog(mainWindow, {
    title: 'Save Mission',
    defaultPath: 'mission.json',
    filters: [{ name: 'JSON Files', extensions: ['json'] }]
  });
  if (!result.canceled && result.filePath) {
    fs.writeFileSync(result.filePath, JSON.stringify(missionData, null, 2));
    return { success: true, filePath: result.filePath };
  }
  return { success: false };
});

// IPC: Load mission from file
ipcMain.handle('load-mission', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: 'Load Mission',
    filters: [{ name: 'JSON Files', extensions: ['json'] }],
    properties: ['openFile']
  });
  if (!result.canceled && result.filePaths.length > 0) {
    const data = fs.readFileSync(result.filePaths[0], 'utf8');
    return { success: true, data: JSON.parse(data) };
  }
  return { success: false };
});
