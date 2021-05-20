from http.server import *
import socketserver
import ssl
import json
import sqlite3


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        try:
            if self.path == "/datafromDB":
                self.wfile.write(database.getValues())

            elif len(self.path) > 1:
                with open(self.path[1:], "rb") as file:
                    self.send_response(200)
                    if "js" in self.path:
                        self.send_header("Content-type", "text/javascript")
                    else:
                        self.send_header("Content-type", "text/css")
                    self.end_headers()
                    self.wfile.write(file.read())

            else:
                self.homepage()
        except Exception as e:
            print(self.path)
            print(e)

    def do_POST(self):
        self.send_response(200)
        length = int(self.headers["content-length"])
        data = self.rfile.read(length)
        database.insertValues(data)

        self.homepage()

    def homepage(self):
        with open("index.html", "rb") as file:
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(file.read())


class CreateDatabase():

    def __init__(self):
        self.dbinit()

    def dbinit(self):
        self.conn = sqlite3.connect("database.db")
        self.c = self.conn.cursor()

        self.c.execute("""
        CREATE TABLE IF NOT EXISTS data (
            lat int(4),
            lng int(4),
            sound int(1),
            CO int(1),
            airquality int(1),
            routeID int(1)
        )
        """)

        data = self.c.execute('select * from data')

        self.collums = list(map(lambda x: x[0], data.description))

    def generateID(self):
        self.c.execute("SELECT * FROM data")
        try:
            lastID = self.c.fetchall()[-1][-1]
            print(lastID)
        except:
            lastID = 0
        return lastID+1

    def insertValues(self, rawData):
        try:
            str = rawData.decode()
            str = str[:str.rfind('}')+1] + ']' + str[str.rfind('}')+1:]

            data = json.loads(str[str.find("["):str.rfind("]") + 1])
            id = self.generateID()

            for item in data:
                values = []
                for key, value in item.items() :
                    if isinstance( value, (frozenset, list, set, tuple,) ):
                        for coord in value:
                            values.append(coord)
                    else:
                        values.append(value)

                values = list(reversed(values))
                values.append(id)

                self.c.execute("""
                INSERT INTO data VALUES (
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?
                )
                """, (values))
                print(values)
            self.conn.commit()

            self.c.execute("SELECT * FROM data")
            data = self.c.fetchall()
            for dataItem in range(len(data)):
                self.c.execute("SELECT * FROM data WHERE lat=%s AND lng=%s" % (data[dataItem][0], data[dataItem][1]))
                duplicates = self.c.fetchall()
                if len(duplicates) > 0:
                    average = [sum(x) for x in zip(*duplicates)]

                    for item in range(len(average)):
                        average[item] /= len(duplicates)

                    for duplicate in duplicates:
                        self.c.execute("""DELETE FROM data WHERE
                        lat=%s AND lng=%s
                        """ % (data[dataItem][0], data[dataItem][1]))

                    average[-1] = duplicates[0][-1]
                    self.c.execute("""
                    INSERT INTO data VALUES (
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?
                    )
                    """, (average))
                    self.conn.commit()

        except Exception as e:
            print(e)

    def getValues(self):
        self.c.execute("SELECT * FROM data")
        return str(self.c.fetchall()).encode()


if __name__ == "__main__":
    database = CreateDatabase()
    server = socketserver.TCPServer(("", 80), Handler)
    server.socket = ssl.wrap_socket(
        server.socket,
        certfile="cert.pem",
        keyfile="key.pem",
        server_side=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(" Recieved Shutting Down")
