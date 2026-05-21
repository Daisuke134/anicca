import io
import sys
from pathlib import Path

from loguru import logger


# src 下のファイルを読み込むために、sys.path にパスを追加
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

from src.modules import describe_dataframe, generate_code


def main() -> None:
    data_path = "data/sample.csv"
    template_file = "src/prompts/generate_code.jinja"
    user_request = "データの概要について教えて"

    with open(data_path, "rb") as fi:
        file_object = io.BytesIO(fi.read())
    data_info = describe_dataframe(file_object=file_object, template_file=template_file)

    response = generate_code(
        data_info=data_info,
        user_request=user_request,
    )
    program = response.content
    logger.info(program.model_dump_json(indent=4))


if __name__ == "__main__":
    main()
