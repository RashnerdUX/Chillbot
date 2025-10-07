# Redis Caching
Here's the link to the study material - [Click Here](https://g.co/gemini/share/5c7049f10074)

## Strategies for Caching
1. **Cache Aside** : Check cache first before accessing db and then store in cache afterwards always 

2. **Write Through** : Write to the cache and db at the same time. Latency issues

3. **Write Back** : Write to Cache first then allow user continue their action. The cache updates the DB afterwards. Risk of data inconsistencies if the Cache crashes before it updates the DB and the data is lost

## Important Caching Data Structures
1. **Hash** : This allows me to store data objects in the cache

2. **List** : This is useful for Redis function as a message broker. Items stored in the list are technically queued from Left to Right so the tasks are completed in an orderly manner. LPUSH to insert and RPOP to remove

3. **Sorted Sets** : Just like normal Python sets, they only store unqiue values and give each of them a score that is used to sort the entire set. This score can be set and can be applied for prioritization and scheduling of tasks. For instance, if the score is based off a priority level or timestamp. Specifically, I can use this to limit a user's action by using the timestamp as the score to count how many actions the user has taken in a time range

## Caching Pipeline (ACID Compliance)
The redis client has an object for ensuring that cache transactions occur with atomicity. The **pipeline()** method is used for this and it is done with a context manager.
Here's an example below where a Sorted set is used to track user's action and implement rate limiting
``` Python
import time
WINDOW_SECONDS = 60
MAX_REQUESTS = 5
USER_KEY = f"rate:user:101"
now = int(time.time() * 1000)
window_start_time = now - (WINDOW_SECONDS * 1000)

# Assuming r has been initialized as a redis client
async with r.pipeline() as pipe:
    # A. Cleanup: Remove old requests (older than 60 seconds)
    pipe.zremrangebyscore(USER_KEY, 0, window_start_time)
        
    # B. Count: Count requests currently in the window
    pipe.zcount(USER_KEY, window_start_time, now)
        
    # C. Execute the first two commands as an atomic batch
    # The result of pipe.execute() is a list matching the order of commands
    results = await pipe.execute() #This is when the logic listed above sequentially occurs at once

# The results of each transaction is stored in the results variable gotten from pipeline.execute()
score = results[0]
count = results[1]
```
>NOTE
>
>> It's possible that another part of the application might mess with the cache and change the key which will affect pipeline.execute()  from working so it's best to use pipeline.watch() to keep track of the key before any work is done on it so at the start of the logic pipeline.watch(CACHE_KEY) is added. If the key changes before pipeline.execute() runs then the transaction is unsuccesful and "redis.exceptions.WatchError" is raised

## Geospatial Data with Caching
Redis can be used to store data for location based queries and it's extremely fast (Low latency). This information is stored in a Sorted Set data structure
When data is stored this way using GEOADD, the following variables are needed:
1. Key
2. Longitude and Latitude of data
3. The value 
Afterwards a user could query the data like "Show me Apple stores within 5 miles of me" and then I'll query the Redis memory like this
> GEORADIUS key longitude latitude distance unit [OPTIONS]
>
> Units can either be
> - m (meters)
> - km (kilometers)
> - mi (miles)
> - ft (feet)