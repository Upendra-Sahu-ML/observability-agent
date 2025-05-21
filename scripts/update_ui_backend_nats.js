#!/usr/bin/env node
/**
 * Script to update the UI backend code to remove the NATS domain parameter
 * 
 * This script modifies the server.js file to remove the jetstreamDomain parameter
 * when connecting to NATS.
 * 
 * Usage:
 *   node update_ui_backend_nats.js
 */

const fs = require('fs');
const path = require('path');

// Path to the UI backend server.js file
const serverJsPath = path.resolve(__dirname, '../ui/backend/server.js');

// Read the file
console.log(`Reading file: ${serverJsPath}`);
let content;
try {
  content = fs.readFileSync(serverJsPath, 'utf8');
  console.log('File read successfully');
} catch (err) {
  console.error(`Error reading file: ${err.message}`);
  process.exit(1);
}

// Replace the NATS connection options to remove the jetstreamDomain parameter
const originalConnectionOptions = `nc = await connect({
      servers: NATS_URL,
      timeout: 5000,
      debug: process.env.DEBUG === 'true',
      jetstreamDomain: NATS_DOMAIN // Add JetStream domain to connection options
    }).catch(err => {`;

const updatedConnectionOptions = `nc = await connect({
      servers: NATS_URL,
      timeout: 5000,
      debug: process.env.DEBUG === 'true'
      // Removed JetStream domain to use default domain
    }).catch(err => {`;

// Replace the connection options
const updatedContent = content.replace(originalConnectionOptions, updatedConnectionOptions);

// Check if the content was actually modified
if (content === updatedContent) {
  console.log('No changes were made to the file. The connection options may have already been updated or the pattern was not found.');
  process.exit(0);
}

// Create a backup of the original file
const backupPath = `${serverJsPath}.bak`;
console.log(`Creating backup at: ${backupPath}`);
try {
  fs.writeFileSync(backupPath, content);
  console.log('Backup created successfully');
} catch (err) {
  console.error(`Error creating backup: ${err.message}`);
  process.exit(1);
}

// Write the updated content back to the file
console.log(`Writing updated content to: ${serverJsPath}`);
try {
  fs.writeFileSync(serverJsPath, updatedContent);
  console.log('File updated successfully');
} catch (err) {
  console.error(`Error writing file: ${err.message}`);
  process.exit(1);
}

console.log('Done!');
