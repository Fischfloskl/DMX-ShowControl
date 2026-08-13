function reconnect(){

    if(!confirm("DMX-Controller neu verbinden? Dieser Vorgang kann 5 sekunden dauern.")){
        return;
    }


    fetch("/api/reconnect", {
        method: "POST"
    })
    .then(response => response.json())
    .then(data => {

        location.reload();

    });

}