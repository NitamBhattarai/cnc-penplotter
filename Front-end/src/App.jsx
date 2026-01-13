import { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [files, setFiles] = useState([]);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [gcodeText, setGcodeText] = useState('');
  const [typedText, setTypedText] = useState('');  // <-- New state for typing input
  const [loading, setLoading] = useState(false);

  // File handlers remain unchanged...
  // handleFileChange, handleDrop, handleDragOver...

  // New handler for typing input change
  const handleTypedTextChange = (e) => {
    setTypedText(e.target.value);
  };

  // Update your existing handleSendToBackend to support both typed text and file text
  const handleSendToBackend = async () => {
    let textToSend = '';

    if (typedText.trim() !== '') {
      // If user typed something, use that text
      textToSend = typedText.trim();
    } else {
      // Otherwise, fallback to uploaded text file
      if (files.length === 0) return alert("Upload a file or type text first!");

      const textFile = files.find(f => f.type === "text/plain");
      if (!textFile) return alert("No text file uploaded and no typed text!");

      // Read the file content asynchronously before sending
      textToSend = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result);
        reader.onerror = () => reject(new Error("Failed to read file"));
        reader.readAsText(textFile);
      });
    }

    try {
      setLoading(true);
      const response = await axios.post(
        "https://cnc-penplotter.onrender.com/gcode",  // <-- Use your backend URL here
        { text: textToSend }
      );
      setGcodeText(response.data);
      alert("G-code generated successfully!");
    } catch (err) {
      console.error("Error:", err);
      alert("Failed to fetch G-code from backend.");
    } finally {
      setLoading(false);
    }
  };

  const downloadGcode = () => {
    if (!gcodeText) return alert("No G-code to download!");
    const blob = new Blob([gcodeText], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "output.gcode";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="app-container">
      <header className="header">
        <h1>Document Preview Studio</h1>
        <p>Upload text files or type text and generate G-code</p>
      </header>

      <main className="main-content">
        <section className="control-panel glass">

          {/* ========== New Typing Input Area ========== */}
          <div className="typing-input glass" style={{ marginBottom: '1rem' }}>
            <label htmlFor="typedText">Type text here:</label>
            <textarea
              id="typedText"
              rows={4}
              value={typedText}
              onChange={handleTypedTextChange}
              placeholder="Type your text to convert to G-code..."
              style={{ width: '100%', padding: '0.5rem', fontSize: '1rem' }}
            />
          </div>

          {/* Existing upload area and file list here... */}
          <div className="upload-area glass"
               onDrop={handleDrop}
               onDragOver={handleDragOver}>
            <div className="upload-content">
              <div className="upload-icon">☁️</div>
              <h3>Drag & Drop Files Here</h3>
              <p>or click browse</p>
              <label className="browse-btn">
                Browse Files
                <input
                  type="file"
                  multiple
                  accept=".txt,image/jpeg,image/png,image/gif"
                  onChange={handleFileChange}
                  hidden
                />
              </label>
              <p className="support-text">
                Supports: Text (.txt), images (.jpg, .png, .gif)
              </p>
            </div>
          </div>

          <div className="uploaded-files">
            <h4>Uploaded Files</h4>
            {files.length === 0 ? (
              <p>No files uploaded yet</p>
            ) : (
              <ul>
                {files.map((file, i) => (
                  <li key={i}>{file.name} ({(file.size / 1024).toFixed(1)} KB)</li>
                ))}
              </ul>
            )}
          </div>

          <div className="action-buttons">
            <button className="download-btn" onClick={handleSendToBackend} disabled={loading}>
              {loading ? "Generating..." : "Generate G-code"}
            </button>
            <button className="download-btn" onClick={downloadGcode}>
              💾 Download G-code
            </button>
          </div>
        </section>

        <section className="preview-panel glass">
          <div className="preview-area">
            {previewUrl ? (
              <img src={previewUrl} alt="Preview" className="preview-image" />
            ) : files.some(f => f.type === 'text/plain') ? (
              <div className="text-placeholder">
                <p>Text document loaded</p>
                <small>(text preview not rendered in this demo)</small>
              </div>
            ) : (
              <div className="empty-preview">
                <div className="icon">📄</div>
                <h4>No content to preview</h4>
                <p>Upload a text file or type text to see the preview here</p>
              </div>
            )}
          </div>

          {gcodeText && (
            <div className="preview-gcode">
              <h4>G-code Preview</h4>
              <pre>{gcodeText}</pre>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
