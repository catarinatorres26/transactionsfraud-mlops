Transactions Fraud Detection — SageMaker MLOps Pipeline
Overview
  This project implements an end-to-end MLOps pipeline for a binary classification problem using AWS SageMaker native components.
  The objective is to demonstrate MLOps orchestration and governance, not model performance.
Pipeline
  SageMaker Training Job (programmatic)
  Hyperparameter Tuning Job (short run)
  Model evaluation
  Model registration (Model Registry)
  Deployment using a custom BYOC container
  Data quality monitoring and drift detection
Training & HPO
  train.py is SageMaker-compatible and HPO-ready.
  Hyperparameters are injected via SageMaker.
  Metrics are logged explicitly for model selection.
Custom Model (BYOC)
  Model packaged in a custom Docker container.
  Custom inference logic and dependencies.
  Follows the BYOC – Single Model pattern shown in class.
Model Registry & Monitoring
  Metrics and artifacts are logged manually.
  Best model is registered in the SageMaker Model Registry.
  Data capture is enabled on the endpoint.
  Data Quality baselines and monitoring schedules are configured.
  Synthetic data drift is simulated for validation.
Architecture
  C4 System Context and Container diagrams describe the solution.
 
