# Notion2PDF
Script to generate a structured PDF from exported Notion HTML pages with support for subpages, images and internal navigation.

## Installation
1. Clone the repository:
   ```
   git clone https://github.com/x3xto/Notion2PDF.git
   cd Notion2PDF
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Install Playwright browsers:
   ```
   playwright install
   ```

## File Preparation
1. Export from Notion:
Open the main page you want to export, click `...` → Export, and select:
    - Format: HTML
    - Enable: Include subpages
    - Enable: Create folders for subpages

2.  Unzip the exported archive. If there are archives inside archives, unpack them as well.
   
3.  Directory Structure: your folder structure should look simplified like this:
    ```
    Notion_Export/
    │   
    │   Main_Page.html
    └───Main_Page/
        │   Sub_Page_1.html
        │   Sub_Page_2.html
        │   Sub_Page_3.html
        │   Sub_Page_4.html
        │   Sub_Page_5.html
        │
        ├───Sub_Page_1/
        │       image.png
        │
        └───Sub_Page_3/
                image.png
    ```
4.  Copy the full path to your `Main_Page.html` file.

## Usage
1. Run the script by providing the path to your main HTML file:
  ```
python notion2pdf.py "/path/to/Main_Page.html"
  ```
2. After execution, two files will be created in the same folder as the input file:
```
combined.html   →    merged structured document
Export.pdf      →    final PDF output
```
<img width="1551" height="684" alt="image" src="https://github.com/user-attachments/assets/19449040-1355-4802-aef5-663453205e90" />
‎ 
<img width="1427" height="435" alt="image" src="https://github.com/user-attachments/assets/8ea7034b-39c9-4a23-b860-821d10e936df" />

### Background & Credits
While searching for a solution to export subpages without a Business subscription, I came across the [NotionPDFGenerator](https://github.com/AlexanderNorup/NotionPDFGenerator) project. However, I found it difficult to get it running. So now we have this python tool. Hope it will be useful :)
