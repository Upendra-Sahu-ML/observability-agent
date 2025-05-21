#!/usr/bin/env node
/**
 * Script to update the UI backend to use standardized stream names
 * 
 * This script modifies the server.js file to use the standardized stream names
 * and to check for stream existence but not try to create them.
 * 
 * Usage:
 *   node update_ui_backend_streams.js
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
let updatedContent = content.replace(originalConnectionOptions, updatedConnectionOptions);

// Replace stream creation attempts with just stream existence checks
// For ROOTCAUSES -> ROOT_CAUSE
const rootcausesPattern = /await js\.streamInfo\('ROOTCAUSES'\);/g;
updatedContent = updatedContent.replace(rootcausesPattern, "await js.streamInfo('ROOT_CAUSE');");

const rootcausesCreatePattern = /await js\.addStream\({\s*name: 'ROOTCAUSES',\s*subjects: \['rootcause\.\*'\]\s*}\);/g;
updatedContent = updatedContent.replace(rootcausesCreatePattern, "console.log('ROOT_CAUSE stream should be created by the NATS server');");

// For all other streams, replace creation attempts with log messages
const streamCreationPattern = /await js\.addStream\({\s*name: '([^']+)',\s*subjects: \[[^\]]+\]\s*}\);/g;
updatedContent = updatedContent.replace(streamCreationPattern, "console.log('$1 stream should be created by the NATS server');");

// Check if the content was actually modified
if (content === updatedContent) {
  console.log('No changes were made to the file. The patterns may not have been found.');
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
