// Welcome message

document.addEventListener("DOMContentLoaded", function()
{
    console.log("SkillSync AI Loaded Successfully");
});


// Dashboard hover animation

const cards = document.querySelectorAll(".dashboard-card");

cards.forEach(card =>
{
    card.addEventListener("mouseenter", function()
    {
        card.style.transform = "scale(1.03)";
    });

    card.addEventListener("mouseleave", function()
    {
        card.style.transform = "scale(1)";
    });
});


// Delete confirmation

const deleteButtons = document.querySelectorAll(".btn-danger");

deleteButtons.forEach(button =>
{
    button.addEventListener("click", function(event)
    {
        const confirmDelete = confirm(
            "Are you sure you want to delete this item?"
        );

        if (!confirmDelete)
        {
            event.preventDefault();
        }
    });
});


// Auto hide alerts

setTimeout(function()
{
    let alerts = document.querySelectorAll(".alert");

    alerts.forEach(alert =>
    {
        alert.style.display = "none";
    });

}, 4000);