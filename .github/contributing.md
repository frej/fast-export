When submitting a patch make sure the commits in your pull request:

* Have good commit messages

  Please read Chris Beams' blog post [How to Write a Git Commit
  Message](https://chris.beams.io/posts/git-commit/) on how to write a
  good commit message. Although the article recommends at most 50
  characters for the subject, up to 72 characters are frequently
  accepted for fast-export.

* Adhere to good [commit
hygiene](http://www.ericbmerritt.com/2011/09/21/commit-hygiene-and-git.html)

  When developing a pull request for hg-fast-export, base your work on
  the current `master` branch and rebase your work if it no longer can
  be merged into the current `master` without conflicts. Never merge
  `master` into your development branch, rebase if your work needs
  updates from `master`.

  When a pull request is modified due to review feedback, please
  incorporate the changes into the proper commit. A good reference on
  how to modify history is in the [Pro Git book, Section
  7.6](https://git-scm.com/book/en/v2/Git-Tools-Rewriting-History).

Please do not submit a pull request if you are not willing to spend
the time required to address review comments or revise the patch until
it follows the guidelines above. A _take it or leave it_ approach to
contributing wastes both your and the maintainer's time.
