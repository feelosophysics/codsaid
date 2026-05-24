import sys
import shlex
from mini_redis_core import MiniRedis
from pub_sub import PubSub

def main():
    db = MiniRedis()
    pubsub = PubSub()
    
    print("Welcome to Mini Redis CLI.")
    print("Type 'exit' or 'quit' to terminate.")
    
    while True:
        try:
            line = input("mini-redis> ").strip()
            if not line:
                continue
                
            if line.lower() in ('exit', 'quit'):
                break
                
            # shlex를 이용해 따옴표 내 공백 문자열을 하나의 인자로 파싱
            args = shlex.split(line)
            if not args:
                continue
                
            # 명령어를 대문자로 정규화
            cmd = args[0].upper()
            
            # 1. String 및 기본 명령어
            if cmd == "SET":
                if len(args) != 3:
                    print("(error) ERR wrong number of arguments for 'SET' command")
                    continue
                try:
                    result = db.set(args[1], args[2])
                    print(result)
                except MemoryError as e:
                    print(str(e))
                    
            elif cmd == "GET":
                if len(args) != 2:
                    print("(error) ERR wrong number of arguments for 'GET' command")
                    continue
                val = db.get(args[1])
                if val is None:
                    print("(nil)")
                else:
                    print(f'"{val}"')
                    
            elif cmd == "DEL":
                if len(args) != 2:
                    print("(error) ERR wrong number of arguments for 'DEL' command")
                    continue
                print(f"(integer) {db.delete(args[1])}")
                
            elif cmd == "EXISTS":
                if len(args) != 2:
                    print("(error) ERR wrong number of arguments for 'EXISTS' command")
                    continue
                print(f"(integer) {db.exists(args[1])}")
                
            elif cmd == "DBSIZE":
                if len(args) != 1:
                    print("(error) ERR wrong number of arguments for 'DBSIZE' command")
                    continue
                print(f"(integer) {db.dbsize()}")
                
            elif cmd == "KEYS":
                if len(args) != 1:
                    print("(error) ERR wrong number of arguments for 'KEYS' command")
                    continue
                keys = db.keys()
                if not keys:
                    print("(empty array)")
                else:
                    for i, k in enumerate(keys):
                        print(f'{i+1}. "{k}"')
                        
            # 2. TTL 관리 명령어
            elif cmd == "EXPIRE":
                if len(args) != 3:
                    print("(error) ERR wrong number of arguments for 'EXPIRE' command")
                    continue
                try:
                    seconds = int(args[2])
                    print(f"(integer) {db.expire(args[1], seconds)}")
                except ValueError:
                    print("(error) ERR value is not an integer or out of range")
                    
            elif cmd == "TTL":
                if len(args) != 2:
                    print("(error) ERR wrong number of arguments for 'TTL' command")
                    continue
                print(f"(integer) {db.ttl(args[1])}")
                
            # 3. 구성 및 모니터링 명령어
            elif cmd == "CONFIG":
                if len(args) != 4 or args[1].upper() != "SET" or args[2].lower() != "maxmemory":
                    print("(error) ERR unknown or malformed 'CONFIG' command")
                    continue
                try:
                    limit = int(args[3])
                    result = db.config_set_maxmemory(limit)
                    print(result)
                except ValueError:
                    print("(error) ERR value is not an integer or out of range")
                    
            elif cmd == "INFO":
                if len(args) != 2 or args[1].lower() != "memory":
                    print("(error) ERR unknown or malformed 'INFO' command")
                    continue
                print(db.info_memory())
                
            # 4. Pub/Sub 명령어 (보너스 구현)
            elif cmd == "SUBSCRIBE":
                if len(args) != 2:
                    print("(error) ERR wrong number of arguments for 'SUBSCRIBE' command")
                    continue
                pubsub.subscribe(args[1])
                print(f"Subscribed to channel '{args[1]}'. Use POLL to read messages.")
                
            elif cmd == "PUBLISH":
                if len(args) != 3:
                    print("(error) ERR wrong number of arguments for 'PUBLISH' command")
                    continue
                receivers = pubsub.publish(args[1], args[2])
                print(f"(integer) {receivers}")
                
            elif cmd == "POLL":
                # 단일 스레드 구조 한계를 극복하기 위해 추가한 커스텀 명령어
                if len(args) != 2:
                    print("(error) ERR wrong number of arguments for 'POLL' command")
                    continue
                msgs = pubsub.poll(args[1])
                if not msgs:
                    print("(empty queue)")
                else:
                    for i, msg in enumerate(msgs):
                        print(f'{i+1}) "{msg}"')
            else:
                print(f"(error) ERR unknown command '{args[0]}'")
                
        except EOFError:
            break
        except KeyboardInterrupt:
            print("\nType 'exit' to terminate.")
            continue
        except Exception as e:
            print(f"(error) Internal error: {str(e)}")

if __name__ == "__main__":
    main()
