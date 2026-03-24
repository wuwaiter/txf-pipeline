use warp::Filter;
use redis::AsyncCommands;

#[tokio::main]
async fn main() {
    let route = warp::path("ws")
        .and(warp::ws())
        .map(|ws: warp::ws::Ws| ws.on_upgrade(handle));

    warp::serve(route).run(([0,0,0,0],9000)).await;
}

async fn handle(ws: warp::ws::WebSocket) {
    let (mut tx, _) = ws.split();

    let client = redis::Client::open("redis://redis:6379").unwrap();
    let mut con = client.get_async_connection().await.unwrap();

    loop {
        let res: Vec<(String, Vec<(String,String)>)> =
            redis::cmd("XREVRANGE")
            .arg("tick:txf").arg("+").arg("-").arg("COUNT").arg(1)
            .query_async(&mut con).await.unwrap();

        if let Some((_, fields)) = res.first() {
            let mut price = "";
            let mut ts = "";

            for (k,v) in fields {
                if k=="price" { price=v; }
                if k=="ts" { ts=v; }
            }

            let msg = format!(r#"{{"price":{},"ts":{}}}"#, price, ts);
            tx.send(warp::ws::Message::text(msg)).await.unwrap();
        }

        tokio::time::sleep(std::time::Duration::from_millis(500)).await;
    }
}