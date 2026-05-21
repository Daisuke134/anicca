import sys
from pathlib import Path

from dotenv import load_dotenv
from e2b_code_interpreter import Sandbox


# src 下のファイルを読み込むために、sys.path にパスを追加
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

from src.modules import execute_code, set_dataframe


load_dotenv()


def main() -> None:
    with Sandbox() as sandbox:
        with open("data/sample.csv", "rb") as fi:
            set_dataframe(sandbox=sandbox, file_object=fi)
        data_thread = execute_code(
            process_id="06_execute_code",
            thread_id=0,
            sandbox=sandbox,
            code="print(df.shape)",
        )
        print(data_thread.model_dump_json(indent=4))


if __name__ == "__main__":
    main()
