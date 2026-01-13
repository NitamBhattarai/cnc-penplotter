import { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [files, setFiles] = useState([]);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [gcodeText, setGcodeText] = useState('');

  // ========== File Upload / Drag & Drop ==========
  const handleFileChange = (e) => {
    const uploadedFiles = Array.from(e.target.files);
    setFiles((prev) => [...prev, ...uploadedFiles]);

    // Preview first file (image only)
    if (uploadedFiles.length > 0) {
      const file = uploadedFiles[0];
      if (file.type.startsWith('image/')) {
        setPreviewUrl(URL.createObjectURL(file));
      } else if (file.type === 'text/plain') {
        setPreviewUrl(null);
      }
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const droppedFiles = Array.from(e.dataTransfer.files);
    setFiles((prev) => [...prev, ...droppedFiles]);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  // ========== Backend / G-code ==========
  const handleSendToBackend = async () => {
    if (files.length === 0) return alert("Upload a file first!");

    const textFile = files.find(f => f.type === "text/plain");
    if (!textFile) return alert("No text file uploaded!");

    const reader = new FileReader();
    reader.onload = async (e) => {
      const content = e.target.result;
      try {
        const response = await axios.post(
          "http://192.168.1.119:5000/gcode",
          { text: content } // Send JSON payload
        );
        console.log("G-code received:", response.data);
        setGcodeText(response.data);
        alert("G-code generated successfully!");
      } catch (err) {
        console.error("Error:", err);
        alert("Failed to fetch G-code from backend.");
      }
    };
    reader.readAsText(textFile);
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
      {/* Header */}
      <header className="header">
        <h1>Document Preview Studio</h1>
        <p>Upload text files and generate G-code</p>
      </header>

      <main className="main-content">
        {/* Left panel - Controls */}
        <section className="control-panel glass">
          {/* Upload Area */}
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

          {/* Uploaded Files */}
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

          {/* Action Buttons */}
          <div className="action-buttons">
            <button className="download-btn" onClick={handleSendToBackend}>
              ⬇️ Generate G-code
            </button>
            <button className="download-btn" onClick={downloadGcode}>
              💾 Download G-code
            </button>
          </div>
        </section>

        {/* Right panel - Preview */}
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
                <p>Upload a text file to see the preview here</p>
              </div>
            )}
          </div>

          {/* G-code Preview */}
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
