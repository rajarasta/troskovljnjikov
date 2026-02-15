import React, { useState, useEffect, useRef } from 'react';
import './spreadsheet.css'; // Link the new CSS file

const columns = [
  { key: 'id', label: 'ID' },
  { key: 'file_id', label: 'File ID' },
  { key: 'sheet_name', label: 'Sheet Name' },
  { key: 'row', label: 'Row' },
  { key: 'item_number', label: 'Item No.' },
  { key: 'description', label: 'Description' }
];

const defaultWidths = [80, 120, 150, 60, 100, 200]; // px

export default function SpreadsheetView({ items }) {
  const [colWidths, setColWidths] = useState(defaultWidths);
  const resizingIdx = useRef(null); // index of column being resized or null
  const startX = useRef(0);
  const initWidth = useRef(0);

  const onMouseDown = (index) => (e) => {
    e.preventDefault();
    resizingIdx.current = index;
    startX.current = e.clientX;
    initWidth.current = colWidths[index];

    const handleMove = (ev) => {
      const delta = ev.clientX - startX.current;
      setColWidths((prev) => {
        const newW = [...prev];
        newW[resizingIdx.current] = Math.max(50, initWidth.current + delta);
        return newW;
      });
    };

    const handleUp = () => {
      document.removeEventListener('mousemove', handleMove);
      document.removeEventListener('mouseup', handleUp);
      resizingIdx.current = null;
    };

    document.addEventListener('mousemove', handleMove);
    document.addEventListener('mouseup', handleUp);
  };

  // Prevent tab navigation while dragging to avoid script jumps.
  useEffect(() => {
    const keyHandler = (e) => {
      if (resizingIdx.current !== null && e.key === 'Tab') {
        e.preventDefault();
        e.stopPropagation();
      }
    };
    document.addEventListener('keydown', keyHandler);
    return () => document.removeEventListener('keydown', keyHandler);
  }, []);

  // Add a class to the table for better handling of text wrapping
  const tableStyle = {
    borderCollapse: 'collapse',
    width: '100%',
    tableLayout: 'fixed'
  };

  // Override row height calculation - we'll set fixed heights or use responsive values based on content  
  const getRowHeightForItem = (item) => {
    // Calculate appropriate row height based on description length
    if (!item || !item.description) return '40px';
    
    const descLength = item.description.length;
    let minHeight = 40; // minimum height in pixels
    
    // Increase height for longer descriptions to ensure good readability  
    if (descLength > 150) {
      return `${Math.min(200, Math.max(minHeight, descLength / 3))}px`;
    } else if (descLength > 80) {
      return `${Math.min(140, Math.max(minHeight, descLength / 2.5))}px`;
    }
    
    // For shorter descriptions, maintain a minimum height
    return '40px';
  };

  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="spreadsheet-table" style={tableStyle}>
        <colgroup>{colWidths.map((w, i) => (<col key={i} style={{ width: `${w}px` }} />))}</colgroup>

        <thead>
          <tr>
            {columns.map((col, idx) => (
              <th
                key={col.key}
                style={{
                  padding: '10px 12px',
                  borderBottom: '1px solid #ddd',
                  textAlign: 'left',
                  fontSize: 'clamp(14px,1.5vmin,16px)',
                  backgroundColor: '#f9fafb',
                  position: 'relative'
                }}>
                {col.label}
                <div
                  onMouseDown={onMouseDown(idx)}
                  style={{
                    position: 'absolute',
                    right: 0,
                    top: 0,
                    width: '5px',
                    height: '100%',
                    cursor: 'ew-resize'
                  }}
                />
              </th>
            ))}
          </tr>
        </thead>

        <tbody>{Array.isArray(items) && items.map((item, idx) => (
          <tr 
            key={idx} 
            style={{ 
              borderBottom: '1px solid #eee',
              minHeight: getRowHeightForItem(item),
              height: getRowHeightForItem(item)
            }}
          >
            {columns.map(col => {
              const value = item[col.key];
              
              // For description column, we might want to adjust styling for better text wrapping
              let cellStyle = {};
              if (col.key === 'description') {
                cellStyle = {
                  padding: '8px 10px',
                  fontSize: 'clamp(12px,1.2vmin,14px)',
                  wordBreak: 'break-word', 
                  whiteSpace: 'normal',
                  minHeight: getRowHeightForItem(item),
                  height: getRowHeightForItem(item)
                };
              } else {
                cellStyle = {
                  padding: '8px 10px',
                  fontSize: 'clamp(12px,1.2vmin,14px)',
                  wordBreak: 'break-word', 
                  whiteSpace: 'normal'
                };
              }
              
              return (<td
                key={col.key}
                style={cellStyle}>{value !== null && value !== undefined ? String(value) : ''}</td>);
            })}
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}