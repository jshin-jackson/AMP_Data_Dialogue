# Data Dialogue

![Data Dialogue Cover](assets/images/cover.png)

**Data Dialogue** is an Applied Machine Learning Prototype (AMP) that enables users to query structured databases using natural language and receive dynamic responses in the form of human-readable summaries, SQL queries, and interactive visualizations.

This AMP empowers non-technical users to interact directly with their data—no SQL skills required. Data Dialogue helps streamline BI and decision-making workflows across business and technical teams.

## Business Use Case

Business users and executives often rely heavily on analysts to extract insights from databases. This adds overhead, slows decisions, and introduces friction in fast-moving environments.

**Data Dialogue** eliminates these delays by:

- Letting users ask questions like “What were the top 3 customer segments by revenue last month?”
- Automatically generating SQL queries behind the scenes
- Returning results in natural language, SQL, and visual chart form

## AMP Components

| Directory                   | Description                                             |
| --------------------------- | ------------------------------------------------------- |
| `0_install-dependencies/` | Scripts to install Python packages in the CAI workspace |
| `1_job-run-python-job/`   | Script to launch the Streamlit app from CAI             |
| `3_app/`                  | Main application with app logic, config, and UI         |
| `assets/`                 | Sample media, templates, and images                     |
| `.project-metadata.yaml`  | AMP specification for Cloudera AI                       |
| `.gitignore`              | Standard project ignore list                            |

## Technologies Used

-**Frontend:** Streamlit

-**Database:** PostgreSQL (local or remote, via SSH)

-**Agent Orchestration:** LangChain

-**LLM Integration:** OpenAI GPT (configurable)

-**SQL Planning & Execution:** Natural language to SQL + evaluation agents

-**Visualization:** Vegalite

## Getting Started

### 🛠️ Setup

1. **Download Repository as a ZIP File**

   On the top of this repository page, click on "Code" green button and "Download ZIP".

2. **Repackage the ZIP**

   The ZIP file downloaded from Github contains "AMP_Data_Dialogue" as the top level directory:
   ```
   AMP_Data_Dialogue-main.zip/
   |--- AMP_Data_Dialogue/
         |--- 0_install-dependencies/
         |--- 1_job-run-python-job/
         |--- 2_model-deploy-model/
         |--- 3_app/
         |--- assets/
         |--- .....
   ```

   Remove the top level directory "AMP_Data_Dialogue" and repackage the ZIP:
   ```bash
   unzip AMP_Data_Dialogue-main.zip
   cd AMP_Data_Dialogue-main
   zip -r AMP_Data_Dialogue .
   ```

3. **Install AMP in CAI Workbench**

   In your Cloudera CAI workbench:

   1. Create a new Project.
   2. Enter the Project name.
   3. Under "Initial Setup", select "AMP".
   4. At the bottom, select "Upload a zip, tar.gz or tgz file".
   5. Click "Browse" and select the AMP ZIP file.
   6. Click "Create Project".


2. **Configure environment variables**

   This AMP uses the following environment variables for configuration:
   * OPENAI_BASE_URL - Leave this blank if using public OpenAI service. If using a private OpenAI compatible endpoint, 
     set the endpoint URL here. E.g. `https://myprivate-endpoint.domain.com:8443/v1`
   * OPENAI_API_KEY - OpenAI API key.
   * DATABASE_URI - SQLAlchemy connection string for the Database. Default is local SQLite3 database that is created
     during the AMP installation.

## Output Modes

Once a natural language query is submitted:

- 🧠 **Response Tab**: Presents a human-readable summary (markdown format)
- 🧾 **SQL Query Tab**: Shows the generated SQL query
- 📊 **Chart Tab**: Renders visualizations when applicable (e.g., pie chart, bar graph)

## License

© 2025 Cloudera, Inc. All Rights Reserved.
