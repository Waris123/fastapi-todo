# main.py
from contextlib import asynccontextmanager
from typing import Union, Optional, Annotated
from fastapi_todo import settings
from sqlmodel import Field, Session, SQLModel, create_engine, select
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from icecream import ic
import logging

# capture logs on log file
logging.basicConfig(level=logging.DEBUG, filename="logs.log", filemode="w")

# DataBase Creating Table Name and Columns 
class Todo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str = Field(index=True)


# Validation applied using Pydantic
class User_data(BaseModel):
     content : str


# only needed for psycopg 3 - replace postgresql
# with postgresql+psycopg in settings.DATABASE_URL
connection_string = str(settings.DATABASE_URL).replace(
    "postgresql", "postgresql+psycopg"
)


# recycle connections after 5 minutes
# to correspond with the compute scale down
engine = create_engine(
    connection_string, connect_args={"sslmode": "require"}, pool_recycle=300
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


# The first part of the function, before the yield, will
# be executed before the application starts.
# https://fastapi.tiangolo.com/advanced/events/#lifespan-function
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Creating tables..")
    create_db_and_tables()
    yield


# Calling lifespan event and setting meta data of application
app = FastAPI(lifespan=lifespan, title="Fast API with DB TODO APP", 
    version="0.0.1",
    servers=[
        {
            "url": "http://0.0.0.0:8888", # ADD NGROK URL Here Before Creating GPT Action
            "description": "Development Server"
        }
        ])
        

# get the current session
def get_session():
    with Session(engine) as session:
        yield session

# default page loads
@app.get("/")
def read_root():
    return {"Hello": "World"}


# Listing of all Todos
@app.get("/todos/", response_model=list[Todo])
def read_todos(session: Annotated[Session, Depends(get_session)]):
        todos = session.exec(select(Todo)).all()
        return todos

# Post Todos
@app.post("/todos/", response_model=Todo)
def create_todo(todo: User_data, session: Annotated[Session, Depends(get_session)]):
        db_todo = Todo(content = todo.content)
        session.add(db_todo)
        session.commit()
        session.refresh(db_todo)
        return db_todo

# Patch Todos
@app.patch("/todos/{todo_id}", response_model=Todo)
def update_todos(todo_id: int, todo: User_data, session: Annotated[Session, Depends(get_session)]):
        
        #with Session(engine) as session:
        # This retrieves the todo item from the database with the specified ID using the session.get() method. 
        # It attempts to fetch a todo item (Todo model) based on the provided todo_id.
        db_todo = session.get(Todo, todo_id)
        
        logging.info("db_todo printing...")
        logging.info(db_todo)
        
        if not db_todo:
            raise HTTPException(status_code=404, detail="Todo not found")
        
        # This line calls the model_dump() method on the todo object (of type User_data). 
        # This likely serializes the todo object into a dictionary, excluding any fields that have not been set (exclude_unset=True).
        todo_data = todo.model_dump(exclude_unset=False)
        
        # This updates the attributes of the db_todo object with the data from todo_data. 
        # The exact behavior of sqlmodel_update depends on its implementation.
        db_todo.sqlmodel_update(todo_data)

        session.add(db_todo)
        session.commit()
        session.refresh(db_todo)
        return db_todo
    
# Delete Todos
@app.delete("/todos/{todo_id}")
def delete_todos(todo_id: int, session: Annotated[Session, Depends(get_session)]):
        todo = session.get(Todo, todo_id)
        if not todo:
            raise HTTPException(status_code=404, detail="Todo ID not found")
        session.delete(todo)
        session.commit()
        return {"message": "Todo Deleted Successfully"}