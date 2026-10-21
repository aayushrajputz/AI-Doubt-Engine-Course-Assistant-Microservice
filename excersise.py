def getUserInfo(name: str , age : int , role : str) -> str :
    return f"{name} is {age} and {role}"




def process_user_payload(payload : dict) -> list[str] :
 tags :list[str] = payload.get("tags",[])

 tags.append("verified")

 return tags

    
def get_active_user_names(users: list[dict]) -> list[str]:
    # Syntax: [OUTPUT for ITEM in LIST if CONDITION]
    return [u["name"] for u in users if u.get("is_active") is True]

    score = 85
    if score >= 90:
        print("grade a")
    elif score >=75 and score < 90:
            print("grade b")
    else:
        print("grade c")        
             
name = ""
if not name :
    print("name is empty")

def check_voting_eligibility(age: int, has_voter_id: bool) -> str:
    if age >= 18 and has_voter_id:
        return "Eligible"
    elif age >= 18 and not has_voter_id:
        return "Not Eligible : Need Voter ID"
    else:
        return "Not Eligible : Under age"

for i in range(5):
    print(i)

for i in range(1,10,2):
    print(i)

    fruits = ["aaple", "banana", "mango"]

    for fruit in fruits:
        print(fruit)
        fruit.append("stawberry")


        for i , fruit in enumerate(fruits):
            print(i , fruit) 

        coutn = 3
        print(f"counting : {coutn}" )
        coutn -= 1
        

        for num in range (6):
            if num == 2:
                continue
    if num ==4:
        break
    print(num) 



    def same_even_numbers(limit: int) -> int :
        total = 0
        for i in range(1, limit + 1):
            if i % 2 == 0:
                total = total + i
        return total 



        db_coordinates = (192,169,1,100) 

        def get_min_max(numbers : list[int]) -> tuple[int,int]:

            return min(numbers),max(numbers)

            lowest,highest = get_min_max([10,5,30,8])
            print(lowest)
            print(highest) 

            tags = {"python", "fastapi","backend","python"}
            print(tags)

            tags.add("docker")
            tags.remove("backend")


            duplicates_ids = [101,102,103,104,105,101,102,103,104]
            unique_id = list(set(duplicates_ids))


            user = {"id": 1, "name": "Aayush", "role": "admin"}

            if "role" in user :
                print(user["role"])

                for key,value in user.items():
                    print(f"{key}:{value}")



        def get_unique_roles(users : list[dict]) -> list[str] :
            roles = set(user["role"] for user in users)
            return list(roles)

            def calulate_sum(*args: int) -> int:
                total = 0
                for num in args :
                    total += num
                    return total

                    price(calulate_sum(1,2))
                    price(calulate_sum(1,2,3,4,5,6,78,9))
                    

                    def build_profile(user_id : int, **kwargs)-> dict:
                        profile = {"user_id": user_id}
                        profile.update(kwargs)
                        return profile

                        print(build_profile(101,name = "aayush",role ="SDE",loc ="banglore"))

                        def log_wrapper(func_name: str , *args, **kwargs):
                            print(f"calling {func_name} with args {args} and kwargs {kwargs}")
 
                def create_api_response(status_code: int, message: str, **kwargs) -> dict:
                    response  = {
                        "status" : status_code,
                        "message" : message
                    }

                    response.update(kwargs)
                    return response


    def divide(a : int , b : int) -> float :
        try :
            result = a/b
        except ZeroDivisionError as e:
            print(f"error:{e}")
            return 0.0
        except TypeError :
            print("invalid types provider")
            return 0.0
        finally :
            print("division attemp complete")
 
        return result
        

        def get_user_balance(user_id: int) -> int :
            if user_id <= 0:
                raise ValueError("user id must greater than 0")

                return 500
                 

        def safe_prase_int(value : str) -> int :
            try:
                return int(value)
            except ValueError :
                print("invalid value", value)
                return 0 
            finally:
                print("parsing complete")


                import databse
                db.connect_db()

                from db import connect_db
                connect_db()

        def main():
            print("application starting")

            if __name__ == "__main__":
                main()



                import asyncio 

                async def fetch_user_data(user_id: int) -> dict:
                    print(f"fetching {user_id}...")
                    await asyncio.sleep(2)

                    return {"id" : user_id, "name": "aayush"}

                    async def main():
                        user = await fetch_user_data(101)
                        print ("received " + user)

                        if __name__ == "__main__":
                            asyncio.run(main())

                 
                    async def process_order(order_id: str, amount: float) -> dict:
                        print(f"processing order {order_id} for ${amount}")

                        await asyncio.sleep(0.5)

                        return {"order_id": order_id, "amount ": amount,"status":"completed"}
                       
