# Instructions for Developers

1.  Install VirtualBox 7.0.14
2.  Import the VM in virtual box using File -> Import Appliance using the provided .ova file
3.  Create the new user
    - Login in the VM as the ubuntu user. The password is ubuntu
    - Open a terminal window
    - Run the following command:
    ```
    sudo ./usercreate.sh
    ```
    - Follow the instructions on the screen to provide the necessary information to create the new user
    - When the procedure is done, log out of the ubuntu user
4.  Initial login
    - Login in the VM as your new user
    - Open a terminal window
    - Run the following command:
    ```
    exec ./userinit.sh
    ```
    - It's now ready to use. There is a dev folder in your home to checkout your projects.