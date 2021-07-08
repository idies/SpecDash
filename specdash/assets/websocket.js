$(document).ready(function(){
    var socketurl = location.origin
    var path = location.pathname + "socket.io"
    var socket = io.connect(socketurl, {path:path})
    socket.on('update', function(msg) {
        update_clientside_app_data()
    });
});

function update_clientside_app_data(data){
    randval = get_uuid()
    update_component_porperty("pull_trigger", {value: randval})
}

function update_component_porperty(id, property){
    //sessionStorage.setItem("store",data)
    var element = document.getElementById(id);
    var key = Object.keys(element).find(key=>key.startsWith("__reactInternalInstance$"));
    var internalInstance = element[key];
    var setProps = internalInstance.return.memoizedProps.setProps;
    setProps(property)
}

function get_uuid() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}
