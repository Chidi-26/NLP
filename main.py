from bot.DialogManger import DialogManager
from bot.intent_sim import SimularityIntentMatcher

if __name__ == "__main__":
    # Train the similarity-based intent matcher once before serving conversations.
    clf = SimularityIntentMatcher()
    clf.fit()
   
    # Plug the trained matcher into the dialog manager that orchestrates the bot flow.
    dm = DialogManager(clf)
    print("Welcome to Chidi's Airway Travel Agency, how may I help you today? (Type 'exit' to quit.)")

    # Keep chatting until the user exits or interrupts the program.
    while True:
        try:
            # Get user input from the console and strops white spaces.
            msg = input("you: ").strip()
            # Allow the user to exit the chat loop.
            if msg.lower() == "exit":
                print("bot: Goodbye!")
                break

            # Get bot response from the dialog manager and print it.
            response = dm.handle(msg)
            print(f"bot: {response}")
            
            # Allow exit on keybaord interupt
        except KeyboardInterrupt:
            print("\n Thank you for your time! Goodbye!")
            break
       
