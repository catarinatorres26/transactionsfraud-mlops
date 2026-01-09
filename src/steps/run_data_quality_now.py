import os
import time
import boto3

AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")
SCHEDULE_NAME = "transactionsfraud-dataquality-schedule"

sm = boto3.client("sagemaker", region_name=AWS_REGION)

def main():
    exec_name = f"{SCHEDULE_NAME}-adhoc-{int(time.time())}"
    sm.start_monitoring_schedule(
        MonitoringScheduleName=SCHEDULE_NAME
    )
    # Nota: start_monitoring_schedule apenas garante que está Enabled.
    # Para forçar execução imediata de facto, criamos um MonitoringExecution via CreateProcessingJob,
    # mas isso é mais verboso. Como alternativa, podemos temporariamente criar um schedule com cron de 1 minuto.
    print("Schedule garantido como Enabled. Se quiser execução imediata, use o modo 'cron 1-min' abaixo.")
    print("Execution label:", exec_name)

if __name__ == "__main__":
    main()
