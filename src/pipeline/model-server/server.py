from quart import Quart
from model_convert import ConvertSkp

app = Quart(__name__)

@app.get("/convert/<filename: str")
async def proc_convert(filename):
    model = ConvertSkp(filename)
    await model.convert()


if __name__ == "__main__":
    app.run()