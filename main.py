from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from operator import itemgetter
from deta import Deta
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")
db = Deta(os.environ["DETA"]).Base("olimpiadas")

app.mount("/static", StaticFiles(directory="static"), name="static")


class Score(BaseModel):
    name: str
    course: int
    score: int
    time: int


categories = {"6": "A", "7": "A", "8": "B", "9": "B", "10": "C", "11": "C"}

categories_options = [6, 7, 8, 9, 10, 11]


@app.post("/add")
async def add_score(score: Score):
    if score.score > 10 or score.score < 0:
        raise HTTPException(status_code=400, detail="Invalid score")

    if score.time > 1200 or score.time < 0:
        raise HTTPException(status_code=400, detail="Invalid time")

    if score.course > 11 or score.course < 6:
        raise HTTPException(status_code=400, detail="Invalid course")

    final_score = {
        "name": score.name,
        "category": categories[str(score.course)],
        "course": score.course,
        "score": score.score,
        "time": score.time,
    }

    id = (
        str(final_score["course"]) + "_" + final_score["name"].replace(" ", "_")
    ).lower()

    final_score["id"] = id

    data = db.put(final_score, id)

    return {"data": data}


@app.get("/{category}")
async def get_leaderboard(request: Request, category: str, response_class=HTMLResponse):
    if not category.isdigit() or int(category) not in categories_options:
        raise HTTPException(status_code=404, detail="Category not found")

    data = db.fetch({"id?contains": category + "_"}).items

    data = sorted(
        sorted(data, key=itemgetter("time")), key=itemgetter("score"), reverse=True
    )

    for i in range(len(data)):
        data[i]["course"] = str(data[i]["course"])

        m, s = divmod(data[i]["time"], 60)

        data[i]["time"] = f"{m:02d}:{s:02d}"

    return templates.TemplateResponse(
        "board.html",
        {
            "request": request,
            "data": data,
            "nums": len(data),
            "category": category.upper(),
        },
    )
