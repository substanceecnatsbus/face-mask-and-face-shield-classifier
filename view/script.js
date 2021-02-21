document.addEventListener("DOMContentLoaded", () => {
    let socketio_client = io();

    socketio_client.on("temperature", temperature => {
        let temperature_input = document.getElementById("temperature");
        temperature_input.value = temperature;
    });

    socketio_client.on("classification", classification => {
        let classification_input = document.getElementById("classification");
        classification_input.value = classification;
    });

    let submit_button = document.getElementById("submit_button");
    submit_button.addEventListener("click", e => {
        e.preventDefault();
        let name = document.getElementById("name").value;
        let contact_number = document.getElementById("contact_number").value;
        let email = document.getElementById("email").value;
        let address = document.getElementById("address").value;
        let temperature = document.getElementById("temperature").value;
        let classification = document.getElementById("classification").value;

        if (name === "" || contact_number === "" || email === "" || address === "" || temperature === "" || classification === "") {
            alert("Please fill out all the remaining fields.");
            return;
        }

        if (classification === "no face") {
            alert("No face detected.\nPlease try again.");
            return;
        }

        let symptoms_others = {
            "cough" : document.getElementById("symptoms_others_cough").checked,
            "fever" : document.getElementById("symptoms_others_fever").checked,
            "headache" : document.getElementById("symptoms_others_headache").checked,
            "difficulty_breathing" : document.getElementById("symptoms_others_difficulty_breathing").checked
        }

        let symptoms = {
            "cough" : document.getElementById("symptoms_cough").checked,
            "fever" : document.getElementById("symptoms_fever").checked,
            "headache" : document.getElementById("symptoms_headache").checked,
            "difficulty_breathing" : document.getElementById("symptoms_difficulty_breathing").checked
        }

        let date_time = (new Date()).toLocaleString().replace(",", "");

        let user_info = {
            "name" : name,
            "contact_number" : contact_number,
            "email" : email,
            "address" : address,
            "date_time" : date_time,
            "temperature": temperature,
            "classification": classification,
            "symptoms_others" : symptoms_others,
            "symptoms": symptoms
        };
        console.log(JSON.stringify(user_info));
        
        socketio_client.emit("user_info", user_info);

        document.getElementById("user_info_form").reset();
    });
});