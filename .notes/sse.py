from quart import Quart, jsonify, render_template_string
import asyncio
import json
from datetime import datetime

app = Quart(__name__)

# Store processing state
processing_jobs = {}

@app.route('/')
async def index():
    """Serve the HTML page"""
    return await render_template_string(HTML_TEMPLATE)

@app.route('/api/process', methods=['POST'])
async def start_process():
    """Start a long-running process"""
    process_id = 'proc-' + datetime.now().strftime('%Y%m%d%H%M%S%f')
    processing_jobs[process_id] = {
        'status': 'processing',
        'percent': 0,
        'message': 'Starting...'
    }
    
    # Start the background task
    asyncio.create_task(long_running_task(process_id))
    
    return jsonify({'process_id': process_id})

async def long_running_task(process_id):
    """Simulate long processing with multiple steps"""
    steps = [
        "Validating input data",
        "Loading datasets",
        "Preprocessing data",
        "Running analysis",
        "Optimizing results",
        "Generating output",
        "Finalizing"
    ]
    
    for step_num, step_name in enumerate(steps):
        await asyncio.sleep(1)  # Simulate work
        overall_percent = int((step_num * 100) / len(steps))
        processing_jobs[process_id] = {
            'status': 'processing',
            'percent': min(overall_percent, 99),
            'message': f'{step_name}... ({overall_percent}%)'
        }
    
    # Final step
    await asyncio.sleep(0.5)
    processing_jobs[process_id] = {
        'status': 'complete',
        'percent': 100,
        'message': 'Processing complete!'
    }

@app.route('/api/status/<process_id>')
async def stream_status(process_id):
    """Stream status updates via SSE"""
    async def generate():
        while True:
            job = processing_jobs.get(process_id, {
                'status': 'not_found',
                'percent': 0,
                'message': 'Process not found'
            })
            yield f"data: {json.dumps(job)}\n\n"
            
            if job.get('status') == 'complete':
                break
            
            await asyncio.sleep(0.5)
    
    return generate(), 200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no'
    }

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Processing Status Monitor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            padding: 40px;
            max-width: 600px;
            width: 100%;
        }
        
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }
        
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        
        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
        }
        
        button {
            flex: 1;
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .btn-start {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .btn-start:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
        }
        
        .btn-start:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
        .btn-reset {
            background: #f0f0f0;
            color: #333;
            flex: 0.3;
        }
        
        .btn-reset:hover {
            background: #e0e0e0;
        }
        
        .status-section {
            display: none;
        }
        
        .status-section.active {
            display: block;
        }
        
        .process-id {
            background: #f5f5f5;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            color: #666;
            word-break: break-all;
        }
        
        .progress-wrapper {
            margin-bottom: 20px;
        }
        
        .progress-label {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            font-size: 14px;
            color: #333;
            font-weight: 500;
        }
        
        .progress-bar {
            width: 100%;
            height: 10px;
            background: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
            transition: width 0.3s ease;
            width: 0%;
        }
        
        .status-message {
            background: #f9f9f9;
            padding: 16px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            color: #333;
            font-size: 14px;
            line-height: 1.6;
        }
        
        .status-message.complete {
            border-left-color: #4caf50;
            background: #f1f8f5;
        }
        
        .status-icon {
            display: inline-block;
            width: 20px;
            height: 20px;
            margin-right: 8px;
            vertical-align: middle;
        }
        
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .checkmark {
            color: #4caf50;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Process Monitor</h1>
        <p class="subtitle">Start a process and watch its progress in real-time</p>
        
        <div class="controls">
            <button class="btn-start" id="startBtn" onclick="startProcess()">Start Processing</button>
            <button class="btn-reset" id="resetBtn" onclick="resetUI()" style="display: none;">Reset</button>
        </div>
        
        <div class="status-section" id="statusSection">
            <div class="process-id">
                Process ID: <span id="processId"></span>
            </div>
            
            <div class="progress-wrapper">
                <div class="progress-label">
                    <span>Progress</span>
                    <span id="percentText">0%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill"></div>
                </div>
            </div>
            
            <div class="status-message" id="statusMessage">
                <div class="spinner status-icon"></div>
                <span id="messageText">Waiting to start...</span>
            </div>
        </div>
    </div>

    <script>
        let eventSource = null;
        let currentProcessId = null;

        async function startProcess() {
            const startBtn = document.getElementById('startBtn');
            const resetBtn = document.getElementById('resetBtn');
            const statusSection = document.getElementById('statusSection');
            
            startBtn.disabled = true;
            
            try {
                const response = await fetch('/api/process', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                const data = await response.json();
                currentProcessId = data.process_id;
                
                document.getElementById('processId').textContent = currentProcessId;
                statusSection.classList.add('active');
                resetBtn.style.display = 'block';
                
                streamStatus(currentProcessId);
            } catch (error) {
                console.error('Error starting process:', error);
                alert('Failed to start process');
                startBtn.disabled = false;
            }
        }

        function streamStatus(processId) {
            // Close previous connection if exists
            if (eventSource) {
                eventSource.close();
            }
            
            eventSource = new EventSource(`/api/status/${processId}`);
            
            eventSource.onmessage = (event) => {
                const status = JSON.parse(event.data);
                updateUI(status);
                
                if (status.status === 'complete') {
                    eventSource.close();
                    onProcessComplete();
                }
            };
            
            eventSource.onerror = (error) => {
                console.error('Stream error:', error);
                eventSource.close();
            };
        }

        function updateUI(status) {
            const percent = status.percent || 0;
            const message = status.message || 'Processing...';
            
            document.getElementById('progressFill').style.width = percent + '%';
            document.getElementById('percentText').textContent = percent + '%';
            document.getElementById('messageText').textContent = message;
        }

        function onProcessComplete() {
            const statusMessage = document.getElementById('statusMessage');
            const messageText = document.getElementById('messageText');
            const icon = statusMessage.querySelector('.status-icon');
            
            statusMessage.classList.add('complete');
            messageText.textContent = '✓ Processing complete!';
            icon.innerHTML = '<span class="checkmark">✓</span>';
            
            document.getElementById('startBtn').disabled = false;
        }

        function resetUI() {
            if (eventSource) {
                eventSource.close();
            }
            
            document.getElementById('statusSection').classList.remove('active');
            document.getElementById('resetBtn').style.display = 'none';
            document.getElementById('startBtn').disabled = false;
            document.getElementById('progressFill').style.width = '0%';
            document.getElementById('percentText').textContent = '0%';
            document.getElementById('messageText').textContent = 'Waiting to start...';
            
            const statusMessage = document.getElementById('statusMessage');
            statusMessage.classList.remove('complete');
            const icon = statusMessage.querySelector('.status-icon');
            icon.innerHTML = '<div class="spinner" style="width: 16px; height: 16px;"></div>';
            
            currentProcessId = null;
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6767, debug=True)
