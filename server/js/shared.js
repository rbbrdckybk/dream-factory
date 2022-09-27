
$(function () {
  var includes = $('[data-include]')
  $.each(includes, function () {
    var file = '/static/_' + $(this).data('include') + '.html'
    $(this).load(file)
  })
})

function copyToClipboard(id) {
    var range = document.createRange();
    range.selectNode(document.getElementById(id));
    window.getSelection().removeAllRanges();
    window.getSelection().addRange(range);
    document.execCommand("copy");
    window.getSelection().removeAllRanges();
}

function niceAlert(titleText, descText, yesText, noText, confirmFunction) {
  swal({
    title: titleText,
    text: descText,
    icon: "warning",
    buttons: true,
    dangerMode: true,
  })
  .then((answer) => {
    if (answer) {
      swal(yesText, {
        icon: "success",
      });
      confirmFunction()
    } else {
      if (noText != "") {
        swal(noText);
      }
    }
  });
}

function niceAlertQuick(titleText, descText, confirmFunction) {
  swal({
    title: titleText,
    text: descText,
    icon: "warning",
    buttons: true,
    dangerMode: true,
  })
  .then((answer) => {
    if (answer) {
      confirmFunction()
    } else {
      if (noText != "") {
        swal(noText);
      }
    }
  });
}
