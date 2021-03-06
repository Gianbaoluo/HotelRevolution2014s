
#***** ROUTING FUNCTIONS by Sara & Simo ***************************************************

from flask import Flask, request, send_from_directory, redirect, url_for, abort, session, render_template
from jinja2 import Environment, PackageLoader
from session import login, logout, sudo
from database import get_item, n_checkin, n_checkout, n_fullrooms, n_freerooms, free_rooms, guest_leaving, price_from_room_id, reserv_info, id_rooms, n_items, add_to_db
from utilities import dataINT_to_datatime, datepick_to_dataINT, dataINT, matching_guest
import sqlite3, time, sets, datetime

app = Flask(__name__, static_folder="templates")

app.secret_key = ".ASF\x89m\x14\xc9s\x94\xfaq\xca}\xe1/\x1f3\x1dFx\xdc\xf0\xf9"

env = Environment(loader=PackageLoader('project', '/templates'))



@app.route('/<path:filename>')
def static_for_hr(filename):
    """Serve the static file from the directory app.static_folder"""
    return app.send_static_file(filename)

@app.route("/login", methods=["GET", "POST"])
def loginpage():
    """
    loginpage()
    This function is called twice:
    - firstly in GET when the system loads, giving in output the mere template.
    - secondly in POST when the user logs in: the page calls login() (imported from functions) to verify the credential, then:
        - if login was successful, redirect the user on "main".
        - else renders the login page again showing the failure message to the user.
    """
    if request.method == "GET":
        template = env.get_template("login.html")
        return template.render()
    
    if request.method == "POST":
        log = login(request.form["name"], request.form["pass"])
        if not log:
            return redirect(url_for("main"))
        else:
            mappa = {"msg" : log , "error" : "TRUE" }
            template = env.get_template("login.html")
            return template.render(mappa)
    return "How could I end up here? :/"


@app.route("/main", methods=["GET"])
def main():
    """
    main()
    This function retrieves only the data shown in the upper div of the mainpage and renders it.
    From here the user can call 3 pages: free_rooms() (to begin the reservation process), reservations() (to search for present reservations), guests() (to search for registered guests).
    """
    if not session.get('logged_in'):
        abort(401)
    today = dataINT()
    mappa = { "today" : dataINT_to_datatime(today), "n_checkin" : n_checkin(today), "n_checkout" : n_checkout(today), "n_occupate" : n_fullrooms(today, today), "n_libere" : n_freerooms(today, today)}
    if n_freerooms(today, today) < 0:
        mappa["msg"]= "Error: the number of today's reservations exceed the total number of rooms. Check the database!"     #Keep this IF...
        mappa["error"] = "TRUE"
    template = env.get_template("main.html")
    return template.render(mappa)


@app.route("/free_rooms", methods=["GET"])
def free_rooms_page():
    """
    free_rooms()
    In this page are shown a list of available rooms in a certain period of time and a form that the receptionist have to fill with the guest's data.
    From this interface the user can choose which room to book and select it. He can also insert the informations about the client, that will be used by the next functions before performing the actual booking process.
    """
    if not session.get('logged_in'):
        abort(401)
    today = dataINT()
    mappa = {"nrooms": n_freerooms(datepick_to_dataINT(request.args["checkin"]), datepick_to_dataINT(request.args["checkout"])), "rooms" : free_rooms(datepick_to_dataINT(request.args["checkin"]), datepick_to_dataINT(request.args["checkout"])), "checkin" : datepick_to_dataINT(request.args["checkin"]), "checkout" : datepick_to_dataINT(request.args["checkout"])}
    template = env.get_template("booking.html")
    return template.render(mappa)
   

@app.route("/confirm-<checkin>-<checkout>", methods=["GET"])
def confirm(checkin, checkout):
    """
    confirm()
    This page shows a sum-up of all the information inserted by the receptionist.
    Guest's data goes through some preprocessing before being shown: it's processed by matching_guest() in order to find if the guest has already been registered in the database. Four cases can be distinguished:
    - matching_guest() found only one perfectly matching row in the database. 
        In this case the infos shown are the ones found in the database.
    - matching_guest() found no perfectly matching rows in the database.
        - matching_guest() found one partial match.
            in this case the receptionist is asked to modify the database in order to update guest's data, instead than inserting a new entry.
        - matching_guest() found more than one partial match.
            In this case The receptionist is asked to choose the guest between the partial matching ones and modify it, or to insert a completely new entry.
        - matching_guest() found no matching rows.
            In this case the data shown are the one the receptionist entered before.

    matching_guest() permits to distinguish between "completely matching" and "partially matching".
    - Perfectly matching: all the fields matches, notes excluded.
    - Partially matching: name, surname, passport matches.
    """
    if not session.get('logged_in'):
        abort(401)
    mappa = {"ckin": dataINT_to_datatime(int(checkin)), "ckout": dataINT_to_datatime(int(checkout))}
    sel_rooms=[]
    for room in free_rooms(checkin, checkout):
        if request.args.get(str(room[0])) == "on":
            sel_rooms.append(room)
    mappa["rooms"] = sel_rooms
#Temo calcoli il prezzo sbagliato!! *************************************  <------------------
    price = 0
    for room in sel_rooms:
        price = price + price_from_room_id(room[0])*(int(checkout)-int(checkin))
    mappa["price"] = price

    guest = []
    keys = []
    match = []
    mappa["error"] = "FALSE"
    for item in ["name", "surname", "email", "passport", "phone", "address", "notes"]:
        if request.args[item] != "":
            guest.append(request.args[item])
            keys.append(item)
    match = matching_guest(keys, guest)
    if not match:
        for item in ["name", "surname", "passport"]:
            if request.args[item] != "":
                guest.append(request.args[item])
                keys.append(item)
        match = matching_guest(keys, guest)
        if not match:
            g = []
            g.append(n_items("guests", "", "") + 1)      #The new ID
            for item in ["name", "surname", "email", "passport", "phone", "address", "notes"]:
                g.append(request.args[item])
                if not request.args[item]:
                    g.append("")
            if g[1] == "" or g[2] == "" or g[4] == "":
                mappa["msg"] = "You must insert name, surname, and passport No of the guest."
                mappa["error"] = "TRUE"
            match.append(g)
            mappa["new_guest"] = "TRUE"
    if len(match)>1:
        mappa["msg"] = "Warning: more than one guest matches the data you entered. Please insert more data."
        mappa["error"] = "TRUE"
    mappa["guests"] = match[0]
    mappa["checkin"] = int(checkin)
    mappa["checkout"] = int(checkout)
    print mappa
    
    template = env.get_template("booking_confirm.html")
    return template.render(mappa)


@app.route("/res_id", methods=["POST"])
def new_reserv_page():
    """
    new_reserv_page():
    This functions perform the actual booking process. If new_guest is set to TRUE, it also write a new entry in the guest's table to record the new user.
    This function returns many reservationIDs as the number of rooms booked and show them to the receptionist.
    It also sends a mail to the guest's email address with the reservation details.
    """
    if not session.get('logged_in'):
        abort(401)
    template = env.get_template("confirm.html")
    mappa = {}
    values = []
    
    for item in ["id_guest", "name", "surname", "email", "passport", "phone", "address", "info"]:
        values.append(request.form[item])
    mappa["guest"] = values
    print 1
    if request.form["new_guest"]:
        result = add_to_db("guests", values)
        if result != "OK":
            mappa["msg"]="An error occured while recording the new guest's data into the database. No reservations made yet. Please retry and be sure that the guest's data inserted are correct."
            mappa["error"]="TRUE"
            return template.render(mappa)
    print 2
    ids = []
    for room in id_rooms():
        print room[0]
        values[0] = n_items("reservations", "", "") + 1         #The new ID
        ids.append(values[0])
        print 4
        if request.form.get(room[0]):
            print 5
            for item in ["id_guest", "id_room", "checkin", "checkout"]:
                values.append(request.form[item])
                result = add_to_db("reservations", values)
                print "ADDED"
                if result != "OK":
                    mappa["msg"]="An error occured while creating the new reservation. Please check what's recorded in the system, in order to spot mistakes in the database's content."
                    mappa["error"]="TRUE"
    print 3
    mappa["id"] = ids
    for i in ids:
        id_room = get_item("reservations", "id_res", i)[1]
        days = get_item("reservations", "id_res", i)[4] - get_item("reservations", "id_res", i)[3]
        tot = tot + get_item("rooms", "id_room", id_room)[3]*days
    mappa["price"] = tot
            

    return template.render(mappa)
    
    
@app.route("/guests", methods=["GET","POST"])
def guests_page():
    """
    guests()
    Shows a list of all the guests recorded in the hotel's database that match the parameter selected in the mainpage.
    Allows the receptionist to view and modify the informations about any guest: this is useful to update the database.
    Includes also the informations about all the reservations made by every guest. TO DO!!
    """
    if not session.get('logged_in'):
        abort(401)
    guests = set([])
    mappa = {}
    n = 0
    if request.method == "GET":
        for field in ["name", "surname", "phone", "passport", "email"]:
            if request.args.get(field):
                n = n + 1
                mappa[field] = request.args.get(field)
                matching = set(get_item("guests", field, request.args.get(field)))
                if n == 1:
                    guests = matching
                else:
                    guests = guests.intersection(matching)
        if len(guests) == 0:
            mappa["msg"] = "Nessun ospite corrisponde ai criteri di ricerca."
            mappa["error"] = "TRUE"

    if request.method == "POST":
        lista = []
        for field in ["id_guest", "name", "surname", "passport", "email", "phone", "address", "info"]:
            lista.append(request.form[field])
        modify_database("guest", "id_guest", id_guest, lista)
        mappa["msg"] = "Database aggiornato correttamente"
        #Regenerate guest's list
        for field in ["name", "surname", "phone", "passport", "address", "email"]:
            if request.form[field]:
                n = n + 1
                mappa[field] = request.form[field]
                matching = set(get_item("guests", field, request.form[field]))
                if n == 1:
                    guests = matching
                else:
                    guests = guests.intersection(matching)
        if len(guests) == 0:
            mappa["msg"] = "An error occured while saving the new guest's data. Please retry."
            mappa["error"] = "TRUE"
                    
    mappa["guest"] = list(guests)

    print mappa
    template = env.get_template("guest.html")
    return template.render(mappa)

@app.route("/reservations")
def reserv_page():
    """
    reserv()
    Allow the receptionist to find a reservation given the ID or the name of the guest.
    In case of many guest with the same name and surname returns the reservations made by both of them: the receptionist can discriminate the users by ID.
    Anyway, a message will alert the user about that.
    """
    if not session.get('logged_in'):
        abort(401)
    reserv = []
    n_res = 0
    mappa = {}
    
    if request.method == "GET":
        if request.args.get("id_res"):
            r = {"id_res" : request.args.get("id_res")}
            reserv.append(reserv_info(get_item("reservations", "id_res", request.args.get("id_res"))))
            if len(reserv) > 1:
                mappa["msg"] = "An error occured: more than one reservation has the selected ID. Check the database!"
                mappa["error"] = "TRUE"
        elif request.args.get("surname"):
            surnames = get_item("guests", "surname", request.args.get("surname"))
            if request.args["name"]:
                names = set(get_item("guests", "name", request.args.get("name")))
                guests = list(set(surnames).intersection(names))
            else:
                guests = surnames
            if len(guests) > 1:
                mappa["msg"] = "More than one guest matches your search. Be careful!"
                mappa["error"] = "TRUE"
            for guest in guests:
                res = get_item("reservations", "id_guest", guest[0])
                reserv.append(reserv_info(get_item("reservations", "id_guest", guest[0])[0]))
                n_res = n_res + len(res)
            
    if request.method == "POST":
        lista = []
        for field in ["name", "surname", "checkin", "checkout", "room", "address", "info"]:
            lista.append(request.form[field])
        #Passo la lista alla funzione di Gio e ottengo un feedback (???) ********************************
        mappa["msg"] = "Database aggiornato correttamente"
        #Regenerate list of resrvations
        if request.form["id_res"]:
            r = {"id_res" : request.form["id_res"]}
            reserv.append(reserv_info(get_item("reservations", "id_res", request.args.get("id_res"))))
            if len(reserv) > 1:
                mappa["msg"] = "An error occured: more than one reservation has the selected ID. Check the database!"
                mappa["error"] = "TRUE"
        elif request.form["surname"]:
            surnames = get_item("guests", "surname", request.form["surname"])
            if request.form["name"]:
                names = set(get_item("guests", "name", request.form["name"]))
                guests = list(set(surnames).intersection(names))
            else:
                guests = surnames
            if len(guests) > 1:
                mappa["msg"] = "More than one guest matches your search. Be careful!"
                mappa["error"] = "TRUE"
            for guest in guests:
                res = get_item("reservations", "id_guest", guest[0])
                reserv.append(reserv_info(get_item("reservations", "id_guest", guest[0])[0]))
                n_res = n_res + len(res)
            
    mappa["n_res"] = n_res
    mappa["reservations"] = reserv
    print mappa
    template = env.get_template("reservations.html")
    return template.render(mappa)


@app.route("/checkout")
def checkout():
    if not session.get('logged_in') or sudo() == "FALSE":
        abort(401)
    today = dataINT()
    template = env.get_template("manager.html")
    mappa= {"lista" : list(guest_leaving(today))}
    mappa["username"] = session["username"]
    mappa["today"] = dataINT_to_datatime(today)
    return template.render(mappa)


@app.route("/revenue")
def revenue():
    template = env.get_template("revenue.html")
    return template.render()


@app.route("/logout")
def logoutpage():
    """
    logoutpage()
    Calls the logout() function in functions.py and then redirects to the login page. In case of failure it must redirect the user on the mainpage with an error message (not implemented yet)
    """
    if logout() == 0:
        mappa = {"msg" : "Logout successfully"}
        template = env.get_template("login.html")
        return template.render(mappa)
    template = env.get_template("login.html")
    mappa["msg"] = "There was a problem during the logout process. Try login and logout again (if necessary)."
    mappa["error"] = "TRUE"
    return template.render(mappa)


#*** ERROR HANDLERS ****************
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(401)
def unauthorized(e):
    return render_template('401.html'), 401

@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500



if __name__ == "__main__":
    app.run(debug=True)
