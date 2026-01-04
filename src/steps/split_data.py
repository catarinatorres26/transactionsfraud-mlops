import os
import pandas as pd
from sklearn.model_selection import train_test_split


def main():
    # Configuração
    INPUT_PATH = "../data/transactions.csv"
    OUTPUT_DIR = "../data/splits"
    TARGET = "Class"
    SEED = 42

    # Verificações básicas
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(f"Não encontrei o ficheiro {INPUT_PATH}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Ler os dados
    df = pd.read_csv(INPUT_PATH)

    if TARGET not in df.columns:
        raise ValueError(f"Coluna alvo '{TARGET}' não existe")

    # Split 70% treino, 30% temporário
    train_df, temp_df = train_test_split(
        df,
        test_size=0.30,
        random_state=SEED,
        stratify=df[TARGET]
    )

    # Split 15% validação, 15% teste
    val_df, test_df = train_test_split(
        temp_df,
        test_size=0.50,
        random_state=SEED,
        stratify=temp_df[TARGET]
    )

    # Guardar ficheiros
    train_df.to_csv(f"{OUTPUT_DIR}/train.csv", index=False)
    val_df.to_csv(f"{OUTPUT_DIR}/val.csv", index=False)
    test_df.to_csv(f"{OUTPUT_DIR}/test.csv", index=False)

    print("Split concluído com sucesso:")
    print(" - data/splits/train.csv:", train_df.shape)
    print(" - data/splits/val.csv:", val_df.shape)
    print(" - data/splits/test.csv:", test_df.shape)


if __name__ == "__main__":
    main()
