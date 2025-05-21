#!/usr/bin/env node
/**
 * Script to update the test scripts to remove the NATS domain parameter
 * 
 * This script modifies the test scripts to remove the jetstreamDomain parameter
 * when connecting to NATS.
 * 
 * Usage:
 *   node update_test_scripts.js
 */

const fs = require('fs');
const path = require('path');

// List of scripts to update
const scriptsToUpdate = [
  'publish_with_domain.js',
  'create_ui_streams.js'
];

// Function to update a script
function updateScript(scriptPath) {
  console.log(`Updating script: ${scriptPath}`);
  
  // Read the file
  let content;
  try {
    content = fs.readFileSync(scriptPath, 'utf8');
    console.log(`File read successfully: ${scriptPath}`);
  } catch (err) {
    console.error(`Error reading file ${scriptPath}: ${err.message}`);
    return false;
  }
  
  // Replace the NATS connection options to remove the jetstreamDomain parameter
  const originalConnectionOptions = `const nc = await connect({
      servers: config.natsUrl,
      timeout: 5000,
      jetstreamDomain: config.domain
    });`;
  
  const updatedConnectionOptions = `const nc = await connect({
      servers: config.natsUrl,
      timeout: 5000
      // Removed JetStream domain to use default domain
    });`;
  
  // Replace the connection options
  const updatedContent = content.replace(originalConnectionOptions, updatedConnectionOptions);
  
  // Check if the content was actually modified
  if (content === updatedContent) {
    console.log(`No changes were made to ${scriptPath}. The connection options may have already been updated or the pattern was not found.`);
    return false;
  }
  
  // Create a backup of the original file
  const backupPath = `${scriptPath}.bak`;
  console.log(`Creating backup at: ${backupPath}`);
  try {
    fs.writeFileSync(backupPath, content);
    console.log(`Backup created successfully for ${scriptPath}`);
  } catch (err) {
    console.error(`Error creating backup for ${scriptPath}: ${err.message}`);
    return false;
  }
  
  // Write the updated content back to the file
  console.log(`Writing updated content to: ${scriptPath}`);
  try {
    fs.writeFileSync(scriptPath, updatedContent);
    console.log(`File updated successfully: ${scriptPath}`);
    return true;
  } catch (err) {
    console.error(`Error writing file ${scriptPath}: ${err.message}`);
    return false;
  }
}

// Update each script
let successCount = 0;
let failureCount = 0;

for (const script of scriptsToUpdate) {
  const scriptPath = path.resolve(__dirname, script);
  if (updateScript(scriptPath)) {
    successCount++;
  } else {
    failureCount++;
  }
}

console.log(`Done! Updated ${successCount} scripts, failed to update ${failureCount} scripts.`);
