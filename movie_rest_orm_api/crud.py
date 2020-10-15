from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc, extract, between
from sqlalchemy import func
from fastapi.logger import logger
import models, schemas

# CRUD for Movie objects
def get_movie(db: Session, movie_id: int):
    # read from the database (get method read from cache)
    # return object read or None if not found
    db_movie = db.query(models.Movie).filter(models.Movie.id == movie_id).first()
    logger.error(f"Movie retrieved from DB: {db_movie.title}")
    logger.error("director: {}".format( 
              db_movie.director.name if db_movie.director is not None else "no director"))
    logger.error(f"actors: {db_movie.actors}")
    return db_movie;

def get_movies(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Movie).offset(skip).limit(limit).all()

def _get_movies_by_predicate(*predicate, db: Session):
    """ partial request to apply one or more predicate(s) to model Movie"""
    return db.query(models.Movie)   \
            .filter(*predicate)

def get_movies_by_title(db: Session, title: str):
    return _get_movies_by_predicate(models.Movie.title == title, db=db)    \
            .order_by(desc(models.Movie.year))                      \
            .all()
            
def get_movies_by_title_part(db: Session, title: str):
    return _get_movies_by_predicate(models.Movie.title.like(f'%{title}%'), db=db)   \
            .order_by(models.Movie.title, models.Movie.year)                       \
            .all()

def get_movies_by_year(db: Session, year: int):
    return _get_movies_by_predicate(models.Movie.year == year, db=db)    \
            .order_by(models.Movie.title)                         \
            .all()

def get_movies_by_range_year(db: Session, year_min: Optional[int], year_max: Optional[int]):
    if year_min is None and year_max is None:
        return None
    if year_min is None:
        predicate = models.Movie.year <= year_max
    elif year_max is None:
        predicate = models.Movie.year >= year_min
    else:
        predicate = between(models.Movie.year, year_min, year_max)
    return _get_movies_by_predicate(predicate, db=db)                  \
            .order_by(models.Movie.year, models.Movie.title)    \
            .all()

def get_movies_by_title_year(db: Session, title: str, year: int):
    return _get_movies_by_predicate(
                    models.Movie.title == title, 
                    models.Movie.year == year,
                    db=db)                                      \
            .order_by(models.Movie.year, models.Movie.title)    \
            .all()

def get_movies_count(db: Session):
    return db.query(models.Movie).count()

def get_movies_count_year(db: Session, year: int):
    return _get_movies_by_predicate(models.Movie.year == year).count()

def get_movies_by_director_endname(db: Session, endname: str):
    return db.query(models.Movie).join(models.Movie.director)      \
            .filter(models.Star.name.like(f'%{endname}')) \
            .order_by(desc(models.Movie.year))  \
            .all()

def get_movies_by_actor_endname(db: Session, endname: str):
    return db.query(models.Movie).join(models.Movie.actors) \
            .filter(models.Star.name.like(f'%{endname}'))   \
            .order_by(desc(models.Movie.year))              \
            .all()
            
def get_movies_count_by_year(db: Session):
    # NB: func.count() i.e. count(*) en SQL
    return db.query(models.Movie.year, func.count())\
            .group_by(models.Movie.year)\
            .order_by(models.Movie.year)\
            .all()
            
def get_movies_stat_duration(db: Session):
    return db.query(models.Movie.year,func.max(models.Movie.duration).label("max_duration"), func.min(models.Movie.duration).label("min_duration"),func.avg(models.Movie.duration).label("mean_duration")) \
            .group_by(models.Movie.year)\
            .order_by(models.Movie.year)\
            .all()
            
def get_stats_movie_by_director(db: Session,min_count: int):
    return db.query(models.Star, func.count(models.Movie.id))\
        .join(models.Movie.director)\
        .group_by(models.Star)\
        .having(func.count(models.Movie.id) >= min_count)\
        .order_by(func.count(models.Movie.id))\
        .all()
    
def update_movie_director(db: Session, movie_id: int, director_id: int):
    db_movie = get_movie(db=db, movie_id=movie_id)
    db_star = get_star(db=db, star_id=director_id)
    if db_movie is None or db_star is None:
        return None
    db_movie.director = db_star
    db.commit()
    return db_movie

def add_movie_actor(db: Session, movie_id: int, star_id: int):
    db_movie = get_movie(db=db, movie_id=movie_id)
    db_star = get_star(db=db, star_id=star_id)
    if db_movie is None or db_star is None:
        return None
    db_movie.actors.append(db_star)
    db.commit()
    return db_movie

def update_movie_actors(db: Session, movie_id: int, star_id: List[int]):
    stars_list = db.query(models.Star).filter(models.Star.id.in_(star_id)).all()
    db_movie = get_movie(db=db, movie_id=movie_id)
    if len(stars_list) != len(star_id):
        return None
    db_movie.actors = stars_list
    db.commit()
    return db_movie
    
def create_movie(db: Session, movie: schemas.MovieCreate):
    # convert schema object from rest api to db model object
    db_movie = models.Movie(title=movie.title, year=movie.year, duration=movie.duration)
    # add in db cache and force insert
    db.add(db_movie)
    db.commit()
    # retreive object from db (to read at least generated id)
    db.refresh(db_movie)
    return db_movie

def update_movie(db: Session, movie: schemas.Movie):
    db_movie = db.query(models.Movie).filter(models.Movie.id == movie.id).first()
    if db_movie is not None:
        # update data from db
        db_movie.title = movie.title
        db_movie.year = movie.year
        db_movie.duration = movie.duration
        # validate update in db
        db.commit()
    # return updated object or None if not found
    return db_movie

def delete_movie(db: Session, movie_id: int):
     db_movie = db.query(models.Movie).filter(models.Movie.id == movie_id).first()
     if db_movie is not None:
         # delete object from ORM
         db.delete(db_movie)
         # validate delete in db
         db.commit()
     # return deleted object or None if not found
     return db_movie
 
    
# CRUD for Star objects
def _get_stars_by_predicate(*predicate, db: Session):
    """ partial request to apply one or more predicate(s) to model Star"""
    return db.query(models.Star)   \
            .filter(*predicate)    

def get_star(db: Session, star_id: int):
    # read from the database (get method read from cache)
    # return object read or None if not found
    return db.query(models.Star).filter(models.Star.id == star_id).first()
    #return db.query(models.Star).get(1)
    #return schemas.Star(id=1, name="Fred")

def get_stars(db: Session, skip: int = 0):
    return db.query(models.Star).filter(models.Star.birthdate.isnot(None)).offset(skip).all()

def get_stars_by_name(db: Session, name: str):
    return _get_stars_by_predicate(models.Star.name == name, db=db) \
            .order_by(models.Star.birthdate)  \
            .all()

def get_stars_by_endname(db: Session, name: str):
    return _get_stars_by_predicate(models.Star.name.like(f'%{name}'), db=db) \
            .order_by(models.Star.birthdate)  \
            .all()

def get_stars_by_birthyear(db: Session, year: int):
    return _get_stars_by_predicate(extract('year', models.Star.birthdate) == year, db=db) \
            .order_by(models.Star.name)  \
            .all()

def get_stars_count(db: Session):
    return db.query(models.Star).count()

def get_star_director_movie(db: Session, movie_id: int):
    db_movie = db.query(models.Movie).filter(models.Movie.id == movie_id)  \
        .join(models.Movie.director).first()
    if db_movie is not None:
        return db_movie.director
    else:
        return None
    
def get_star_director_movie_by_title(db: Session, title: str):
    db_movies = db.query(models.Movie).filter(models.Movie.title.like(f'%{title}%')) \
        .join(models.Movie.director)  
    return [ db_movie.director for db_movie in db_movies ]

def get_stats_by_stars(db: Session,min_count: int):
    return db.query(models.Star, func.count(models.Movie.id), func.min(models.Movie.year), func.max(models.Movie.year))\
        .join(models.Movie.actors)\
        .group_by(models.Star)\
        .having(func.count(models.Movie.id) >= min_count)\
        .order_by(desc(func.count(models.Movie.id)))\
        .all()

def create_star(db: Session, star: schemas.StarCreate):
    # convert schema object from rest api to db model object
    db_star = models.Star(name=star.name, birthdate=star.birthdate)
    # add in db cache and force insert
    db.add(db_star)
    db.commit()
    # retreive object from db (to read at least generated id)
    db.refresh(db_star)
    return db_star

def update_star(db: Session, star: schemas.Star):
    db_star = db.query(models.Star).filter(models.Star.id == star.id).first()
    if db_star is not None:
        # update data from db
        db_star.name = star.name
        db_star.birthdate = star.birthdate
        # validate update in db
        db.commit()
    # return updated object or None if not found
    return db_star

def delete_star(db: Session, star_id: int):
     db_star = db.query(models.Star).filter(models.Star.id == star_id).first()
     if db_star is not None:
         # delete object from ORM
         db.delete(db_star)
         # validate delete in db
         db.commit()
     # return deleted object or None if not found
     return db_star