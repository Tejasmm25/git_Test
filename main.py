# This Python file uses the following encoding: utf-8
import sys
import os
import re
import sys
import pdfplumber
import datetime
import time
import easygui
import mysql.connector

from PySide2.QtGui import QGuiApplication
from PySide2.QtQml import QQmlApplicationEngine
from PySide2.QtCore import QObject, Slot, Signal, QTimer, QUrl



class Product():
    def __init__(self, prod_data_row ):
        self.id = prod_data_row[0]
        self.name = prod_data_row[1]
        self.category = prod_data_row[2]
        self.sub_category = prod_data_row[3]
        self.price = prod_data_row[4]  # type - decimal.Decimal
        self.quant_available = prod_data_row[5]
        self.quant_cap = prod_data_row[6]

    def display(self):
        print("-----------------------")
        print(f"prod_id = {self.id}")
        print(f"prod_name = {self.name}")
        print(f"prod_category = {self.category}")
        print(f"prod_sub_category = {self.sub_category}")
        print(f"prod_price = {self.price}")
        print(f"prod_quant_current = {self.quant_available}")
        print(f"prod_quant_cap = {self.quant_cap}")
        print("-----------------------\n")


class PurchaseOrder():
    # def __init__(self, po_raw_data ):
    def __init__(self):
        self.id = None
        self.client = ""
        self.client_email = ""
        self.client_contact = ""
        self.delivery_date = ""
        self.total_amt = ""
        self.order_details = []
        # self.raw_data = po_raw_data

    def display(self):
        print("-----------------------")
        print(f"id = {self.id}")
        print(f"client = {self.client}")
        print(f"client_email = {self.client_email}")
        print(f"client_contact = {self.client_contact}")
        print(f"delivery_date = {self.delivery_date}")
        print(f"total_amt = {self.total_amt}")
        print(f"order_details = {self.order_details}")
        print("-----------------------\n")

class Order():
    def __init__(self, order_data_row ):
        self.id = str(order_data_row[0])
        self.date = order_data_row[1]
        self.total = str(order_data_row[2])
        self.customer_name = order_data_row[3]
        self.customer_contact = order_data_row[4]
        self.paid = "yes" if order_data_row[5] == 1 else "no"
        self.details = eval(order_data_row[6])

    def display(self):
        print("-----------------------")
        print(f"order_id = {self.id}")
        print(f"order_date = {self.date}")
        print(f"order_total = {self.total}")
        print(f"order_customer_name = {self.customer_name}")
        print(f"order_customer_contact = {self.customer_contact}")
        print(f"order_paid = {self.paid}")
        print(f"order_details = {self.details}")
        print("-----------------------\n")


class MainWindow(QObject):
    def __init__(self):
        QObject.__init__(self)

        # QTimer - Run Timer
        self.timer = QTimer()
        self.timer.timeout.connect(lambda: self.setTime())
        self.timer.start(1000)
        self.total = 0
        self.po_objs = []
        self.product_objs = []
        self.order_objs = []
        self.path_changed = False

    # DB connection
    db = mysql.connector.connect(
         host = "localhost",
         user = "root",
         passwd = "root",
         database = "ocr_project_db"
    )
    print("Succefully connected to the Database")
    mycursor = db.cursor()

    # Load the DB data for productListModel
#    mycursor.execute("SELECT * FROM product")
#    fetch_result = mycursor.fetchall()
#    product_objs = []
#    for prod_data_row in fetch_result:
#      product_objs.append(Product(prod_data_row))

##    for product in product_objs:
##      product.display()



    # Purchase Order Page functionality
    @Slot(str)
    def sendScanningSignal(self, tempText):
        self.scanningDataStr.emit(str("Scanning folder for purchase orders..."))

    @Slot(str)
    def getPurchaseOrderData(self, folder_opt):

        print("func called -------------")
        if folder_opt ==  "custom":
            fpath = easygui.fileopenbox()
            fpath = fpath.split("\\")
            fname = fpath.pop(-1)
            po_pdfs = [fname]
            fpath = "\\".join(fpath)

            if not self.path_changed:
                os.chdir(fpath)
                self.path_changed = True

        else:
            if not self.path_changed:
                os.chdir("Purchase Orders")
                self.path_changed = True

            po_pdfs_list = os.listdir()
            po_pdfs = [f_name for f_name in po_pdfs_list if ".pdf" in f_name]

        # OCR
        for purch_order in po_pdfs:
            # before converting to ocr
            purch_order_name = purch_order.split("PO_")  # PO name
            purch_order_name, purch_order_id = purch_order_name[0], purch_order_name[1].split(".pdf")[0]

            for po_obj in self.po_objs:
                if po_obj.id == purch_order_id:
                    print("duplicate")
                    return

            if folder_opt !=  "custom":
                with pdfplumber.open(purch_order) as pdf:
                    page = pdf.pages[0]
                    text = page.extract_text()
                    # print(f"raw pdf read{text}")
            else:
                with pdfplumber.open(fpath) as pdf:
                    page = pdf.pages[0]
                    text = page.extract_text()

            # OCR the pdf file
            try:
                os.system(f'ocrmypdf {purch_order} output.pdf')
            except:
                print("problem converting to ocr pdf")

            # Extract the processed file
            with pdfplumber.open('output.pdf') as pdf:
                page = pdf.pages[0]
                raw_text = page.extract_text(x_tolerance=2)
                # print(f"ocr pdf read{raw_text}")

            os.remove("output.pdf")


            # Perform regex to parse the data #

            raw_text = re.sub('\n', 'NWLINE', raw_text)

            # Email
            emails = re.findall("(?=Email).*(?=VENDOR)", raw_text)
            email = emails[0].split(":")[1].strip(" ")
            email = email.split(" ")[0]

            # Contact no
            contact_no = re.findall("Phone:(.*)Email", raw_text)[0]
            contact_no = re.findall("Phone:(.*)NWLINE", contact_no[5:])[0]
            contact_no = re.sub(' ', '', contact_no)
            contact_no = contact_no[:9]

            # Delivery Date
            dd = re.findall("Date:(.*)NWLINE", raw_text)[0].strip(" ")
            delivery_date = ""
            for char in dd:
                if not char.isalpha():
                    delivery_date += char

            # Total amount
            total = re.findall("Other(.*)Authorized", raw_text)[0].strip(" ")
            total = re.findall("Total(.*)NWLINE", total)[0].strip(" ")
            total_amt = ""
            for c in total:
                if c.isdigit():
                    total_amt+=c

            # Cart product
            cart = re.findall(r'olay(.*)Sub', raw_text)[0]
            cart_items_raw = cart.split("NWLINE")
            cart_items_raw.reverse()
            cart_items = []

            for item in cart_items_raw:
                for char in item:
                    if char.isalpha() and "Unit  Code" not in item:
                        cart_items.append(item)
                        break

            cart_items.reverse()

            order_details = []
            for item in cart_items:
                item_details = []
                item_data = item.split(" ")
                item_data = [d for d in item_data if d]
                item_quant = item_data.pop(0)
                item_code  = item_data.pop(0)
                item_price_total = item_data.pop(-1)
                item_price_total = re.sub(',', '', item_price_total)
                item_price = item_data.pop(-1)
                item_price = re.sub(',', '', item_price)
                item_name = " ".join(item_data)

                item_details = [item_name, item_quant, item_price]
                order_details.append(item_details)

            po_obj = PurchaseOrder()
            po_obj.id = purch_order_id
            po_obj.client = purch_order_name
            po_obj.client_email = email
            po_obj.client_contact = contact_no
            po_obj.delivery_date = delivery_date
            po_obj.total_amt = total_amt
            po_obj.order_details = order_details
            self.po_objs.append(po_obj)
            print("PO OBJ APPENDED")

        print("All pdfs scanned.")
        self.scannedDataStr.emit(str(""))


    @Slot(str)
    def loadPurchaseOrderData(self, tempText):
        self.clearPurchListDataStr.emit("")
        for po in self.po_objs:
            self.purchaseOrderDataStr.emit(po.id+"!"+po.total_amt+"!"+po.delivery_date+"!"+po.client+"!"+po.client_contact+"!"+po.client_email)

    @Slot(str)
    def getPurchOrderDetails(self, order_id):
        self.refreshPurchOrderDetailsDataStr.emit("")

        for po_obj in self.po_objs:
            print(po_obj.id)
            print(order_id)
            if po_obj.id == order_id:
                for item in po_obj.order_details:
                    item_name, item_quantity, item_price = item[0], str(item[1]), str(item[2])
                    self.purchOrderDetailsDataStr.emit(item_name+"@"+item_quantity+"@"+item_price)



    @Slot(str)
    def acceptOrder(self, order_id):
        order_cart = []
        for po_obj in self.po_objs:
            if po_obj.id == order_id:

                paid = 0
                db_query = f'INSERT INTO ocr_project_db.order(order_total, order_customer_name, order_customer_contact, order_paid, order_details) VALUES ({po_obj.total_amt}, "{po_obj.client}", "{po_obj.client_contact}", {paid}, "{po_obj.order_details}");'
                print(f"insert query: {db_query}")
                order_cart = po_obj.order_details
                try:
                    self.mycursor.execute(db_query)
                    self.db.commit()
                except Exception as e:
                    print("-----------Error inserting order data into order table---------")
                    self.orderAcceptedDataStr.emit(f"Order not accepted, following error occured: {e}")
                    input()
                print("Successfully inserted the order data into Order Table")

                fname = po_obj.client + "PO_" + po_obj.id + ".pdf"
                old_fpath = os.getcwd() + "\\" + fname
                new_fpath = re.sub("Purchase Orders", "Accepted Orders", old_fpath)
                os.rename(old_fpath, new_fpath)

                self.po_objs.remove(po_obj)
                print(f"length of po_objs: {len(self.po_objs)}")

                self.clearPurchListDataStr.emit("")
                self.refreshBillingDataStr.emit("")
                self.orderAcceptedDataStr.emit("Order placed succefully")

        for item in order_cart:
            print(item)
            selected_item_name, selected_item_quant = item[0], item[1]
            db_query = f"UPDATE product SET prod_quant_current = prod_quant_current - {selected_item_quant} WHERE prod_name = '{selected_item_name}' "
            print(f"UPDATE QUERY : {db_query}")
            try:
                self.mycursor.execute(db_query)
                self.db.commit()
                print(f"Successfully updated {selected_item_name}'s quantity")
            except Exception as e:
                print("-----------Error updating {selected_item_name}'s quantity---------")
                print(e)

        self.refreshInvDataStr.emit("")
        print("Refreshed Inv data")
        self.refreshProdDataStr.emit("")
        print("Refreshed Prod data")
        self.refreshBillingDataStr.emit("")
        print("Refreshed bill data")


    # Home Page functionality
    @Slot(str)
    def loadProductData(self, tempText):
        self.product_objs[:] = []
        self.mycursor.execute("SELECT * FROM product")
        fetch_result = self.mycursor.fetchall()
        for prod_data_row in fetch_result:
#          prod_quantity = prod_data_row[5]
#          if prod_quantity > 0:
           self.product_objs.append(Product(prod_data_row))
        print("Product data loaded")

    #    for product in product_objs:
    #      product.display()

    @Slot(str)
    def getProductData(self, tempText):
        for product in self.product_objs:
#            self.productDataStr.emit(str(product.name+"@"+str(int(product.price))))
            self.productDataStr.emit(str(product.name+"@"+str(int(product.price))+"@"+str(int(product.quant_available))))
        print("Product data updated")

    # Filter and update the productListModel acc to the given searchQuery
    @Slot(str)
    def filterProductData(self, searchQuery):
        for product in self.product_objs:
            if searchQuery.lower() in product.name.lower():
                self.productDataStr.emit(str(product.name+"@"+str(int(product.price))))

    # Cart functionality
    cart = []
    @Slot(str)
    def addCartItem(self, itemData):
        is_available = True
        itemName, itemQuant = itemData.split("@")
        for prod in self.product_objs:
            if prod.name == itemName:
                itemPrice = prod.price
                break
        self.cart.append((itemName, itemQuant, str(int(itemPrice) * int(itemQuant))))
#        print(f"Current items in cart: {self.cart}")

    @Slot(str)
    def removeCartItem(self, itemName):
#        print("Total cart items: {len(self.cart)}")
        self.cart[:] = [item for item in self.cart if item[0] != itemName]
#        print(f"updated list : {self.cart}")
#        print(f"Total cart items: {len(self.cart)}")


    @Slot(str)
    def clearCart(self, tempText):
        self.cart[:] = []

    @Slot(str)
    def getCartTotal(self, labelstr):
        self.total = sum([int(item[2]) for item in self.cart])
        self.setCartTotal.emit(labelstr + str(self.total))

    @Slot(str)
    def getCartData(self, tempText):
        if len(self.cart) == 0:
            print("Cart is empty.")
            return
        for item in self.cart:
            self.cartDataStr.emit(str(item[0]+"@"+item[1]+"@"+item[2]))

    @Slot(str)
    def placeOrder(self, customerInfo):
        customer_name, customer_contact, paid = customerInfo.split("@")
        if not customer_name and not customer_contact:
            self.invalidFormDataStr.emit("Invalid info.\nPlease enter customer name and contact ")
            return
        elif not customer_name:
            self.invalidFormDataStr.emit("Invalid info.\nPlease enter customer name ")
            return
        elif not customer_contact:
            self.invalidFormDataStr.emit("Invalid info.\nPlease enter customer contact ")
            return

        paid = 1 if paid == "true" else 0
        db_query = f'INSERT INTO ocr_project_db.order(order_total, order_customer_name, order_customer_contact, order_paid, order_details) VALUES ({self.total}, "{customer_name}", "{customer_contact}", {paid}, "{self.cart}");'
        print(f"insert query: {db_query}")
        try:
            self.mycursor.execute(db_query)
            self.db.commit()
        except Exception as e:
            print("-----------Error inserting order data into order table---------")
            input()
        print("Successfully inserted the order data into Order Table")

        # Deduct quantity from the quant_available in DB
        for item in self.cart:
            print(item)
            selected_item_name, selected_item_quant = item[0], item[1]
#            for prod in self.product_objs:
#                if prod.name == selected_item_name:
#                    quant_available = int(prod.quant_available)
#            updated_quant = quant_available - selected_item_quant
            db_query = f"UPDATE product SET prod_quant_current = prod_quant_current - {selected_item_quant} WHERE prod_name = '{selected_item_name}' "
            print(f"UPDATE QUERY : {db_query}")
            try:
                self.mycursor.execute(db_query)
                self.db.commit()
                print(f"Successfully updated {selected_item_name}'s quantity")
            except Exception as e:
                print("-----------Error updating {selected_item_name}'s quantity---------")
                print(e)

        self.refreshInvDataStr.emit("")
        print("Refreshed Inv data")
        self.refreshProdDataStr.emit("")
        print("Refreshed Prod data")
        self.validPlaceOrderDataStr.emit("")



    # Bill/order functionality

    @Slot(str)
    def loadOrderData(self, tempText):
        self.order_objs[:] = []
        self.mycursor.execute("SELECT * FROM ocr_project_db.order")
        fetch_result = self.mycursor.fetchall()
        for order_data_row in reversed(fetch_result):
          self.order_objs.append(Order(order_data_row))
        print("Billing page data loaded")
        for order in self.order_objs:
            order.display()


    @Slot(str)
    def getOrderData(self, filter):

        if "@" in filter:
            filter, filter_query = filter.split("@")
            print(f"filter: {filter}, filter query: {filter_query}")

        if filter == "Unpaid":
            for order in self.order_objs:
                if order.paid == "no":
                    order_time = order.date.strftime("%H:%M:%S")
                    order_date = order.date.strftime("%d/%m/%Y")
                    order_str = order.id + "@"  + order_time + "@" + order_date + "@" + order.total + "@" + order.customer_name + "@" + order.customer_contact + "@" + order.paid
                    self.orderDataStr.emit(order_str)
            print("Billing page filtered & updated(filter = Unpaid)")
        elif filter == "cn":
            for order in self.order_objs:
                if order.customer_name.lower() == filter_query.lower():
                    order_time = order.date.strftime("%H:%M:%S")
                    order_date = order.date.strftime("%d/%m/%Y")
                    order_str = order.id + "@"  + order_time + "@" + order_date + "@" + order.total + "@" + order.customer_name + "@" + order.customer_contact + "@" + order.paid
                    self.orderDataStr.emit(order_str)
            print("Billing page filtered & updated(filter = Customer Name)")
        elif filter == "cc":
            for order in self.order_objs:
                if order.customer_contact == filter_query:
                    order_time = order.date.strftime("%H:%M:%S")
                    order_date = order.date.strftime("%d/%m/%Y")
                    order_str = order.id + "@"  + order_time + "@" + order_date + "@" + order.total + "@" + order.customer_name + "@" + order.customer_contact + "@" + order.paid
                    self.orderDataStr.emit(order_str)
            print("Billing page filtered & updated(filter = Customer Contact)")
        elif filter == "date":
            for order in self.order_objs:
                if order.date.strftime("%d/%m/%Y") == filter_query:
                    order_time = order.date.strftime("%H:%M:%S")
                    order_date = order.date.strftime("%d/%m/%Y")
                    order_str = order.id + "@"  + order_time + "@" + order_date + "@" + order.total + "@" + order.customer_name + "@" + order.customer_contact + "@" + order.paid
                    self.orderDataStr.emit(order_str)
                else:
                    print(f'filter_query: {filter_query} & og: {order.date.strftime("%d/%m/%Y")} did not match')
            print("Billing page filtered & updated(filter = Order Date)")
        else:
            for order in self.order_objs:
                order_time = order.date.strftime("%H:%M:%S")
                order_date = order.date.strftime("%d/%m/%Y")
                order_str = order.id + "@"  + order_time + "@" + order_date + "@" + order.total + "@" + order.customer_name + "@" + order.customer_contact + "@" + order.paid
                self.orderDataStr.emit(order_str)
            print("Billing page updated")


    @Slot(str)
    def markPaid(self, order_id):
        db_query = f"UPDATE `ocr_project_db`.`order` SET `order_paid` = 1 WHERE (`order_id` = '{order_id}');"
        try:
            self.mycursor.execute(db_query)
            self.db.commit()
        except Exception as e:
            print("-----------Error inserting order data into order table---------")
            print(e)
            input()
        print("Successfully updated the order as paid in Order Table")


    @Slot(str)
    def getOrderDetails(self, order_id):
        self.refreshOrderDetailsDataStr.emit("")
        for order in self.order_objs:
            print(f"current id: {order.id}")
            print(f"Match id : {order_id}")
            if order.id == order_id:
                print("matched")
                for item in order.details:
                    item_name, item_quantity, item_price = item[0], str(item[1]), str(item[2])
                    self.orderDetailsDataStr.emit(item_name+"@"+item_quantity+"@"+item_price)
                return

    # Inventory functionality
    @Slot(str)
    def getInvData(self, tempText):
        for product in self.product_objs:
            inv_str = str(product.id)+"@"+product.name+"@"+str(int(product.price))+"@"+str(product.quant_available)+"@"+str(product.quant_cap)+"@"+product.category+"@"+product.sub_category
            self.invDataStr.emit(inv_str)
            print(f"INV STRING TO QML\n {inv_str}")
#            self.invDataStr.emit(str(product.id)+"@"+product.name+"@"+str(int(product.price))+"@"+str(product.quant_available)+"@"+str(product.quant_cap))
    @Slot(str)
    def addNewProd(self, prod_data):
        prod_name, prod_category, prod_sub_category, prod_price, prod_quant_current, prod_quant_cap = prod_data.split("@")
        if not all([prod_name, prod_category, prod_sub_category, prod_price]):
            self.invalidFormDataStr.emit("Invalid entry!\nMissing one or more details.")
            return
        elif prod_quant_cap == "0":
            self.invalidFormDataStr.emit("Invalid entry!\n Max quantity should be more than 0")
            return

        print("\nAdding the following product to DB")
        print(f"prod name: {prod_name} ")
        print(f"prod category: {prod_category} ")
        print(f"prod prod sub category: {prod_sub_category} ")
        print(f"prod price: {prod_price} ")
        print(f"prod quant current: {prod_quant_current} ")
        print(f"prod quant cap: {prod_quant_cap} ")
        columns_str = "prod_name, prod_category, prod_sub_category, prod_price, prod_quant_current, prod_quant_cap"
        values_str = f'"{prod_name}", "{prod_category}", "{prod_sub_category}", {prod_price}, {prod_quant_current}, {prod_quant_cap}'
        db_query = f'INSERT INTO product({columns_str}) VALUES ({values_str});'
        print(f"insert query: {db_query}")
        txn_status = ""
        try:
            self.mycursor.execute(db_query)
            self.db.commit()
            print("Successfully inserted the product data into Product Table")
            txn_status = "Product added succefully."
        except Exception as e:
            print("-----------Error inserting product data into Product table---------")
            txn_status = "Failed to add the product, please try again."

        self.newProdAddedDataStr.emit(txn_status)
        print("TXN STATUS EMITTED")
        self.refreshInvDataStr.emit("")
        print("Refreshed Inv data")
        self.refreshProdDataStr.emit("")
        print("Refreshed Prod data")



    @Slot(str)
    def editProd(self, prod_data):
        prod_data = prod_data.split("@")
        update_vals = f"prod_name = '{prod_data[1]}', prod_category = '{prod_data[2]}', prod_sub_category = '{prod_data[3]}', "
        update_vals += f"prod_price = {prod_data[4]}.00, prod_quant_current = {prod_data[5]}, prod_quant_cap = {prod_data[6]}"
        db_query = f'UPDATE product SET {update_vals} WHERE prod_id={prod_data[0]};'
        print(f"update query: {db_query}")
        txn_status = ""
        try:
            self.mycursor.execute(db_query)
            self.db.commit()
            print("Successfully updated the product in the Product Table")
            txn_status = "Product has been updated."
        except Exception as e:
            print("-----------Error updating product from Product table---------")
            txn_status = "Failed to update the product, please try again."

        self.editProdDataStr.emit(txn_status)
        print("UPDATE TXN STATUS EMITTED")
        self.refreshInvDataStr.emit("")
        print("Refreshed Inv data")
        self.refreshProdDataStr.emit("")
        print("Refreshed Prod data")

    @Slot(str)
    def deleteProd(self, prod_id):
        db_query = f'DELETE FROM product WHERE prod_id={prod_id};'
        print(f"delete query: {db_query}")
        txn_status = ""
        try:
            self.mycursor.execute(db_query)
            self.db.commit()
            print("Successfully deleted the product from the Product Table")
            txn_status = "Product has been removed."
        except Exception as e:
            print("-----------Error deleting product from Product table---------")
            txn_status = "Failed to remove the product, please try again."

        self.deleteProdDataStr.emit(txn_status)
        print("DELETE TXN STATUS EMITTED")
        self.refreshInvDataStr.emit("")
        print("Refreshed Inv data")
        self.refreshProdDataStr.emit("")
        print("Refreshed Prod data")


    # Signals

    # Signal Purchase Order data
    purchaseOrderDataStr = Signal(str)
    # Scanning pdf files
    scanningDataStr = Signal(str)

    # Scanning pdf files
    scannedDataStr = Signal(str)

    # PurchaseOrder details
    purchOrderDetailsDataStr = Signal(str)

    refreshPurchOrderDetailsDataStr = Signal(str)

    orderAcceptedDataStr = Signal(str)

    clearPurchListDataStr = Signal(str)

    refreshBillingDataStr = Signal(str)

    # Signal Set Data
    printTime = Signal(str)

    # Signal Visible
    isVisible = Signal(bool)

    # Text String
    textField = ""

    # Signal Prod data
    productDataStr = Signal(str)

    # Signal Refresh Prod data
    refreshProdDataStr = Signal(str)

    # Signal Set Cart Total
    setCartTotal = Signal(str)

    # Signal Cart data
    cartDataStr = Signal(str)

    # Signal Order data
    orderDataStr = Signal(str)

    # Signal Order Details data
    orderDetailsDataStr = Signal(str)

    # Signal refresh Order details data
    refreshOrderDetailsDataStr = Signal(str)

    # Signal Inv data
    invDataStr = Signal(str)

    # Signal refresh Inv data
    refreshInvDataStr = Signal(str)

    # Signal new prod added
    newProdAddedDataStr = Signal(str)

    # Signal delete prod
    deleteProdDataStr = Signal(str)

    # Signal edit prod
    editProdDataStr = Signal(str)

    # Invalid form
    invalidFormDataStr = Signal(str)

    # valid place order
    validPlaceOrderDataStr = Signal(str)

    # Read Text
    @Slot(str)
    def getTextField(self, text):
        self.textField = text

    # Show / Hide Rectangle
    @Slot(bool)
    def showHideRectangle(self, isChecked):
        print("Is rectangle visible: ", isChecked)
        self.isVisible.emit(isChecked)

    # Set Timer Function
    def setTime(self):
        now = datetime.datetime.now()
        formatDate = now.strftime("Time: %H:%M:%S %p of %d/%m/%Y")
#        print(formatDate)
        self.printTime.emit(formatDate)


if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    # Get Context
    main = MainWindow()
    engine.rootContext().setContextProperty("backend", main)

    # Set App Extra Info
    app.setOrganizationName("Tejas Mandlik")
    app.setOrganizationDomain("N/A")

    # Load QML File
    engine.load(os.path.join(os.path.dirname(__file__), "qml/main.qml"))

    if not engine.rootObjects():
        sys.exit(-1)
    sys.exit(app.exec_())

    
