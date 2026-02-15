import React from 'react';

interface SpreadsheetViewProps {
  items: any[];
}

const columns = [
  { key: 'id', label: 'ID' },
  { key: 'file_id', label: 'File ID' },
  { key: 'sheet_name', label: 'Sheet Name' },
  { key: 'row', label: 'Row' },
  { key: 'item_number', label: 'Item No.' },
  { key: 'description', label: 'Description' }
];

export default function SpreadsheetView({ items }: SpreadsheetViewProps) {
  // Override row height calculation - we'll set fixed heights or use responsive values based on content  
  const getRowHeightForItem = (item: any) => {
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

  const rows = items.slice(0, 6);
  
  return (
    <div style={{ overflowX: 'auto', width: '100%' }}>
      <table className="spreadsheet-table" 
        style={{ borderCollapse: 'collapse', width: '100%', tableLayout: 'fixed' }}>
        <thead>
          <tr>{columns.map(col => (
            <th key={col.key} style={{ padding: '8px 12px', borderBottom: '1px solid #ddd', textAlign: 'left', fontSize: 'clamp(14px,1.5vmin,16px)', backgroundColor: '#f9fafb' }}>{col.label}</th>
          ))}</tr>
        </thead>
        <tbody>{rows.map(item => (
            <tr 
              key={item.id} 
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
                    padding: '6px 10px',
                    fontSize: 'clamp(12px,1.2vmin,14px)',
                    minHeight: getRowHeightForItem(item),
                    height: getRowHeightForItem(item)
                  };
                } else {
                  cellStyle = {
                    padding: '6px 10px',
                    fontSize: 'clamp(12px,1.2vmin,14px)'
                  };
                }
                
                return (<td 
                  key={col.key} 
                  style={{
                    ...cellStyle,
                    wordBreak: 'break-word', // Better control of text breaking
                    whiteSpace: 'normal'      // Allow wrapping
                  }}
                >
                  {value !== null && value !== undefined ? String(value) : ''}
                </td>);
              })}
            </tr>
          ))}</tbody>
      </table>
    </div>
  );
}
