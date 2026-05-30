# Zagimore ETL Procedure Tester

## Overview

This project develops an automated testing system for evaluating student Zagimore ETL and data warehouse projects. The system is designed to help a professor or graduate assistant automatically access each student’s databases, execute row count check procedures, validate ETL outputs, and generate reports showing which procedures passed or failed.

Currently, this process is done manually by opening each student account, running stored procedures, checking row counts, and recording whether each student’s ETL work is correct. This project aims to automate that process and make the evaluation more consistent, transparent, constructive, and scalable.

The project focuses on comparing source tables with the corresponding fact and dimension tables in the data staging and data warehouse databases. The final goal is to make student project evaluation fair and transparent while also providing constructive feedback that students can use to revise and improve their work.

## Project Purpose

The purpose of this project is to create a Python and SQL-based automation tool that tests the validity of student Zagimore ETL projects.

The system will take a list of student usernames as input, automatically access each student’s Zagimore-related databases, execute the required row count check procedures, and generate a report showing which procedures executed successfully and which failed.

This tool is intended to reduce the manual effort required by the professor or graduate assistant while improving the consistency and fairness of student project evaluation.


## Goals

The main goal of this project is to develop an automated testing system that evaluates student Zagimore ETL projects in a fair, transparent, and constructive way.

Specific goals include:

1. Create and test row count check procedures that compare source tables with the corresponding fact and dimension tables in the data staging and data warehouse databases.

2. Create Python scripts that test the validity of student ETL projects by automatically accessing each student’s databases and executing the appropriate row count checks.

3. Generate a report for each student that lists all procedures executed successfully and all procedures that failed.

4. Clearly state the type of failure for each failed procedure or validation check.

5. Provide constructive feedback that students can use to revise and improve their ETL projects.

6. Reduce the manual effort required by the professor or graduate assistant when evaluating multiple student database projects.


## Use Case

A professor or graduate assistant prepares a CSV file containing the usernames of students in the class. The script reads this file and loops through each student account.

For each student, the script searches for the relevant Zagimore databases, runs the required ETL and row count check procedures, checks the results, and records the outcome in a final report.

Instead of manually checking one student project at a time, the professor or graduate assistant can run one script that evaluates all listed students and produces a structured report.

## Expected Input

The main input is a CSV file containing student usernames.

## Author

**Godfrey M. Kanotunga**  
Graduate Student, Applied Data Science  
Clarkson University  

## Acknowledgements

Special thanks to **Professor Boris Jukic** for his guidance, support, and project direction.

This project was developed based on Professor Jukic’s recommendation to create a practical automation tool for testing student Zagimore ETL and data warehouse projects. His guidance helped define the purpose, goals, validation process, and expected outcomes of the project.
