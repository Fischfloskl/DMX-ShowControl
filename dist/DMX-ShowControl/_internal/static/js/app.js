function reconnect(){

    if(!confirm("Reconnect the DMX controller? This process may take 5 seconds.")){
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