from flask import Blueprint, render_template, request, flash, jsonify, abort, redirect, url_for, session
from flask_login import login_required, current_user
from .models import Note, Product, Cart, Payment, CreditCard
from . import db
import json
import stripe


views = Blueprint('views', __name__)

    # if request.method == 'POST': 
    #     note = request.form.get('note')#Gets the note from the HTML 

    #     if len(note) < 1:
    #         flash('Note is too short!', category='error') 
    #     else:
    #         new_note = Note(data=note, user_id=current_user.id)  #providing the schema for the note 
    #         db.session.add(new_note) #adding the note to the database 
    #         db.session.commit()
    #         flash('Note added!', category='success')

    # return render_template("home.html", user=current_user)

@views.route('/')
@login_required
def home():
    products = Product.query.all()
    return render_template('new.html', products = products, user = current_user)


@views.route('/product/<int:id>')
@login_required
def product_detail(id):
    # Query the Product table for the product with the specified id
    product = Product.query.get(id)
    
    # If no product was found with that id, return a 404 error
    if not product:
        abort(404)
    
    # Render the product detail template with the product and the current user
    return render_template('product_detail.html', product=product, user=current_user)

@views.route('/cart')
def cart():
    # Get the user's cart from the database
    user_id = current_user.id
    cart = Cart.query.filter_by(user_id=user_id).first()
    
    # If the user has no items in their cart, display a message
    if not cart or not cart.product_list:
        # return render_template('cart.html', message='Your cart is empty.', user = current_user)
        return render_template('test.html', user_id = user_id, cart = cart)
    
    # print(cart.product_list[0])
    # Split the product IDs and quantities into lists
    if cart.product_list!='':
        product_ids = [int(x) for x in cart.product_list.split(',')]
    else:
        product_ids = []
    # print(product_ids)
    if cart.quantity_list!='':
        quantities = [int(x) for x in cart.quantity_list.split(',')]
    else:
        quantities = []
    # print(quantities)
    
    # Get the product objects for each ID
    products = []
    for product_id in product_ids:
        product = Product.query.get(product_id)
        # print(product.price)
        if product:
            products.append(product)
    product_quantities = []
    # Zip the products and quantities together for display
    # product_quantities = zip(products, quantities)
    # print(product_quantities[0])  
    total = 0  
    for i in range(0, len(quantities)):
        total = total+ quantities[i]*products[i].price
        product_quantities.append([products[i], quantities[i]])

    return render_template('cart.html', products = products, quantities = quantities, user = current_user, product_quantities = product_quantities, total = total)
    # return render_template('cart.html', product_quantities=product_quantities, total_price=total_price, user = current_user)



@views.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    # Get the product ID from the form data
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity'))
    # Get the user's cart from the database
    user_id = current_user.id
    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart:
        cart = Cart(user_id=user_id, product_list='', quantity_list='')
    if cart.product_list!='':
        product_ids = [int(x) for x in cart.product_list.split(',')]
    else:
        product_ids = []
    # print(product_ids)
    if cart.quantity_list!='':
        quantities = [int(x) for x in cart.quantity_list.split(',')]
    else:
        quantities = []
    # print(quantities)
    
    # If the product is already in the cart, increase the quantity by 1
    print(product_ids)
    print(quantities)
    print(product_id)
    # bool = True
    # for k in range (0, len(product_ids)):
    #     print(product_ids[k] == product_id)
    #     if product_ids[k] == product_id:
    #         quantities[k] += quantity
    #         bool = False
    #         break
    # cart.quantity_list = ','.join(str(q) for q in quantities)
    # print(bool)
    # if bool:
    #     cart.product_list += f',{product_id}'
    #     cart.quantity_list += f',{quantity}'

    if product_id in product_ids:
        product_index = product_ids.index(int(product_id))
        print(product_index)
        quantities[product_index] += quantity
        cart.quantity_list = ','.join(str(q) for q in quantities)
        
    else:
        cart.product_list += f',{product_id}'
        cart.quantity_list += f',{quantity}'


    # Save the cart to the database
    db.session.add(cart)
    db.session.commit()
    
    # Redirect the user back to the cart page
    return redirect(url_for('views.cart'))

# @views.route('/delete-note', methods=['POST'])
# def delete_note():  
#     note = json.loads(request.data) # this function expects a JSON from the INDEX.js file 
#     noteId = note['noteId']
#     note = Note.query.get(noteId)
#     if note:
#         if note.user_id == current_user.id:
#             db.session.delete(note)
#             db.session.commit()

#     return jsonify({})



@views.route("/payment", methods=["GET", "POST"])
@login_required
def payment():
    if request.method == "POST":
        # get the payment details from the form
        payment_method = request.form.get("payment-method")
        card_number = request.form.get("card-number")
        expiry_date = request.form.get("expiry-date")
        cvv = request.form.get("cvv")
        name_on_card = request.form.get("Name as on card")

        # look up the user's credit card by card number
        credit_card = CreditCard.query.filter_by(card_number=card_number, user_id=current_user.id).first()

        # check if credit card is valid
        if not credit_card or credit_card.expiry_date != expiry_date or credit_card.cvv != cvv or credit_card.name_on_card != name_on_card:
            return render_template("payment_failure.html")

        # create a new payment object
        payment = stripe.PaymentIntent.create(
            amount=1000, # set the payment amount in cents
            currency="usd",
            payment_method_types=[payment_method],
            payment_method_data={
                payment_method: {
                    "card": {
                        "number": card_number,
                        "exp_month": int(expiry_date.split("/")[0]),
                        "exp_year": int(expiry_date.split("/")[1]),
                        "cvc": cvv,
                        "name": name_on_card,
                    }
                }
            },
        )

        # check the payment status
        if payment.status == "succeeded":
            # create a new Payment record in the database
            new_payment = Payment(user_id=current_user.id, amount=1000, status="succeeded")
            db.session.add(new_payment)
            db.session.commit()
            return render_template("payment_success.html", payment_id=payment.id)
        else:
            return render_template("payment_failure.html")

    # render the payment page template
    return render_template("payment.html", user=current_user)

