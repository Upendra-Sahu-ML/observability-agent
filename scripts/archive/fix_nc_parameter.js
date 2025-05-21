#!/usr/bin/env node
/**
 * Fix the nc parameter in all functions that use it
 * 
 * This script updates all functions in server.js that use the nc variable
 * to add the nc parameter to the function signature.
 */

const fs = require('fs');
const path = require('path');

// Path to the server.js file
const serverJsPath = path.join(__dirname, '..', 'ui', 'backend', 'server.js');

// Read the server.js file
let serverJs = fs.readFileSync(serverJsPath, 'utf8');

// Functions that need to be fixed
const functionsToFix = [
  {
    name: 'getRootCauseData',
    oldSignature: 'async function getRootCauseData(js, alertId)',
    newSignature: 'async function getRootCauseData(js, nc, alertId)'
  },
  {
    name: 'getTracingData',
    oldSignature: 'async function getTracingData(js, traceId, service)',
    newSignature: 'async function getTracingData(js, nc, traceId, service)'
  },
  {
    name: 'getNotificationData',
    oldSignature: 'async function getNotificationData(js)',
    newSignature: 'async function getNotificationData(js, nc)'
  },
  {
    name: 'getPostmortemData',
    oldSignature: 'async function getPostmortemData(js)',
    newSignature: 'async function getPostmortemData(js, nc)'
  },
  {
    name: 'getRunbookData',
    oldSignature: 'async function getRunbookData(js, runbookId)',
    newSignature: 'async function getRunbookData(js, nc, runbookId)'
  }
];

// Update the function signatures
for (const func of functionsToFix) {
  serverJs = serverJs.replace(func.oldSignature, func.newSignature);
}

// Update the getData function to pass nc to the functions
const getDataFunctionUpdates = [
  {
    oldCode: 'data = await getRootCauseData(js, alertId);',
    newCode: 'data = await getRootCauseData(js, nc, alertId);'
  },
  {
    oldCode: 'data = await getTracingData(js, traceId, tracingService);',
    newCode: 'data = await getTracingData(js, nc, traceId, tracingService);'
  },
  {
    oldCode: 'data = await getNotificationData(js);',
    newCode: 'data = await getNotificationData(js, nc);'
  },
  {
    oldCode: 'data = await getPostmortemData(js);',
    newCode: 'data = await getPostmortemData(js, nc);'
  },
  {
    oldCode: 'data = await getRunbookData(js, runbookId);',
    newCode: 'data = await getRunbookData(js, nc, runbookId);'
  }
];

// Update the getData function
for (const update of getDataFunctionUpdates) {
  serverJs = serverJs.replace(update.oldCode, update.newCode);
}

// Write the updated server.js file
fs.writeFileSync(serverJsPath, serverJs);

console.log('Successfully updated server.js with nc parameter fixes');
