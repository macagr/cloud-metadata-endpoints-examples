# Google cloud run shell

This code was taken from [https://github.com/matti/google-cloud-run-shell](https://github.com/matti/google-cloud-run-shell). All the credit goes to the corresponding authors. I have only used it for research purposes on Metadata endpoints. The authors have created a demo: "Getting shell access to cloud run in 60 seconds" at https://www.youtube.com/watch?v=P-XiXIESPC8

This code was built with:

  - https://github.com/jpillora/chisel
  - https://github.com/matti/lolbear


## Heroku chisel bridge
First thing required is a Heroku account and the Heroku CLI installed. With these things you can then create a heroku app. For example, mychisel.herokuapp.com:

    cd heroku-chisel
    bin/deploy mychisel

## Second step is to deploy a container in Cloud Run: 

    bin/deploy my-project mychisel.herokuapp.com

## Next step is to start client in your own computer that tunnels traffic:

    chisel client mychisel.herokuapp.com 9999:localhost:2222

## Finally, SSH can be used to access the Cloud Run container:

    ssh -p 9999 localhost
