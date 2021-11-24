import time, sys

def main():
    try:
        with open('health.log', 'r+') as f:
            if int(time.time()) - int(f.readline()) > 60:
                sys.exit(1)
            sys.exit(0)
    except Exception as e:
        sys.exit(1)

if __name__ == "__main__":
    main()