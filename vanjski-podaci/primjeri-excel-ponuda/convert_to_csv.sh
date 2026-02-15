#!/bin/bash

# Create output directory if it doesn't exist
mkdir -p csv_output

# Convert each Excel file to CSV
for file in *.xlsx; do
    if [ -f "$file" ]; then
        echo "Converting $file to CSV..."
        libreoffice --headless --convert-to csv --outdir csv_output "$file"
    fi
done

echo "Conversion complete!"
