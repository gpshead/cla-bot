import ErrorPanel, { ErrorProps } from "./error";
import { Component, ReactElement } from "react";
import { Button } from "@material-ui/core";
import Preloader from "./preloader";


interface FormViewProps {
  submit: () => Promise<void>
  edit: () => void
  cancel: () => void
  editing: boolean
}


interface FormViewState {
  error?: ErrorProps,
  loading: boolean,
  submitting: boolean
}


/**
 * Generic component to handle views of editable objects.
 * This component handles error views, loaders, cancel buttons to revert
 * changes in a centralized way.
 */
export default class FormView
extends Component<FormViewProps, FormViewState> {

  constructor(props: FormViewProps) {
    super(props)

    this.state = {
      error: undefined,
      loading: false,
      submitting: false
    }
  }

  submit(): void {
    this.setState({
      error: undefined,
      submitting: true
    })

    this.props.submit()
    .then(() => {
      this.setState({
        error: undefined,
        submitting: false
      })
    }, () => {
      this.setState({
        error: {},
        submitting: false
      })
    }).catch(error => {
      this.setState({
        error: {
          message: `${error}`
        },
        submitting: false
      })
    })
  }

  cancel(): void {
    this.props.cancel();
  }

  edit(): void {
    this.props.edit();
  }

  renderButtons(): ReactElement[] {
    const elements: ReactElement[] = []
    if (this.props.editing) {
      elements.push(
        <Button
          key="submit-button"
          variant="contained"
          color="primary"
          onClick={() => this.submit()}
        >
          Submit
        </Button>
      )
      elements.push(
        <Button
          key="cancel-button"
          variant="contained"
          color="primary"
          onClick={() => this.cancel()}
        >
          Cancel
        </Button>
      )
    } else {
      elements.push(
        <Button
          key="edit-button"
          variant="contained"
          color="primary"
          onClick={() => this.edit()}
        >
          Edit
        </Button>
      )
    }
    return elements
  }

  render(): ReactElement {
    const state = this.state;
    const props = this.props;

    return <div className="edit-view">
      {state.submitting && <Preloader className="overlay" />}
      {props.children}
      {state.error && <ErrorPanel {...state.error} />}
      <div className="buttons-area">
        {this.renderButtons()}
      </div>
    </div>
  }
}
